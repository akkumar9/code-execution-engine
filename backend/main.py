from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import docker
import uuid
import asyncio
from pathlib import Path

app = FastAPI()

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Docker client
docker_client = docker.from_env()

# Temp directory for code files
TEMP_DIR = Path("/tmp/code_execution")
TEMP_DIR.mkdir(exist_ok=True)


class CodeExecutor:
    """Handles code execution in Docker containers"""
    
    LANGUAGE_CONFIGS = {
        "python": {
            "image": "python:3.11-slim",
            "file_ext": "py",
            "compile_cmd": None,
            "run_cmd": "python {filename}"
        },
        "cpp": {
            "image": "gcc:latest",
            "file_ext": "cpp",
            "compile_cmd": "g++ -o program {filename} -std=c++17",
            "run_cmd": "./program"
        },
        "java": {
    "image": "eclipse-temurin:17-jre",
    "file_ext": "java",
    "compile_cmd": "javac {filename}",
    "run_cmd": "java {classname}"
}
    }
    
    def __init__(self):
        # Pull images on startup
        for lang, config in self.LANGUAGE_CONFIGS.items():
            try:
                docker_client.images.get(config["image"])
            except docker.errors.ImageNotFound:
                print(f"Pulling {config['image']}...")
                docker_client.images.pull(config["image"])
    
    async def execute(self, code: str, language: str, websocket: WebSocket):
        """Execute code and stream output via WebSocket"""
        
        if language not in self.LANGUAGE_CONFIGS:
            await websocket.send_json({
                "type": "error",
                "data": f"Unsupported language: {language}"
            })
            return
        
        config = self.LANGUAGE_CONFIGS[language]
        execution_id = str(uuid.uuid4())
        work_dir = TEMP_DIR / execution_id
        work_dir.mkdir()
        
        try:
            # Write code to file
            filename = f"main.{config['file_ext']}"
            code_file = work_dir / filename
            code_file.write_text(code)
            
            await websocket.send_json({
                "type": "status",
                "data": "Starting execution..."
            })
            
            # Compile if needed
            if config["compile_cmd"]:
                await self._run_container(
                    config["image"],
                    config["compile_cmd"].format(filename=filename),
                    work_dir,
                    websocket,
                    "Compiling..."
                )
            
            # Run code
            classname = "main" if language == "java" else None
            run_cmd = config["run_cmd"].format(
                filename=filename,
                classname=classname
            )
            
            await self._run_container(
                config["image"],
                run_cmd,
                work_dir,
                websocket,
                "Running..."
            )
            
            await websocket.send_json({
                "type": "status",
                "data": "Execution complete"
            })
            
        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "data": str(e)
            })
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(work_dir, ignore_errors=True)
    
    async def _run_container(self, image: str, command: str, 
                            work_dir: Path, websocket: WebSocket, 
                            status_msg: str):
        """Run command in Docker container and stream output"""
        
        await websocket.send_json({
            "type": "status",
            "data": status_msg
        })
        
        # Resource limits
        container = docker_client.containers.run(
            image,
            command=f"sh -c '{command}'",
            volumes={str(work_dir): {'bind': '/workspace', 'mode': 'rw'}},
            working_dir='/workspace',
            network_mode='none',  # No network access
            mem_limit='256m',     # 256MB RAM limit
            cpu_period=100000,
            cpu_quota=50000,      # 50% CPU
            detach=True,
            remove=True,
            stdout=True,
            stderr=True
        )
        
        # Stream logs
        try:
            for line in container.logs(stream=True, follow=True):
                decoded = line.decode('utf-8')
                await websocket.send_json({
                    "type": "output",
                    "data": decoded
                })
                await asyncio.sleep(0.01)  # Prevent overwhelming client
            
            # Wait for container and get exit code
            result = container.wait(timeout=10)
            exit_code = result['StatusCode']
            
            if exit_code != 0:
                await websocket.send_json({
                    "type": "error",
                    "data": f"Process exited with code {exit_code}"
                })
        
        except docker.errors.APIError as e:
            await websocket.send_json({
                "type": "error",
                "data": f"Docker error: {str(e)}"
            })


executor = CodeExecutor()


@app.websocket("/ws/execute")
async def execute_code(websocket: WebSocket):
    """WebSocket endpoint for code execution"""
    await websocket.accept()
    
    try:
        # Receive code and language
        data = await websocket.receive_json()
        code = data.get("code", "")
        language = data.get("language", "python")
        
        # Execute
        await executor.execute(code, language, websocket)
        
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "data": f"Server error: {str(e)}"
        })
    finally:
        await websocket.close()


@app.get("/")
async def root():
    return {"message": "Code Execution Engine API"}


@app.get("/languages")
async def get_languages():
    """Get supported languages"""
    return {"languages": list(CodeExecutor.LANGUAGE_CONFIGS.keys())}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)