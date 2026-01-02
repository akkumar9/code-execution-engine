import React, { useState, useRef, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import './App.css';

function App() {
  const [code, setCode] = useState('print("Hello, World!")');
  const [language, setLanguage] = useState('python');
  const [output, setOutput] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const wsRef = useRef(null);

  const EXAMPLE_CODE = {
    python: 'print("Hello, World!")\nfor i in range(5):\n    print(f"Count: {i}")',
    cpp: '#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << "Hello, World!" << endl;\n    return 0;\n}',
    java: 'public class main {\n    public static void main(String[] args) {\n        System.out.println("Hello, World!");\n    }\n}'
  };

  const executeCode = () => {
    if (isExecuting) return;
    
    setIsExecuting(true);
    setOutput('Connecting...\n');

    const ws = new WebSocket('ws://localhost:8000/ws/execute');
    wsRef.current = ws;

    ws.onopen = () => {
      setOutput('Connected. Sending code...\n');
      ws.send(JSON.stringify({
        code: code,
        language: language
      }));
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      switch (message.type) {
        case 'status':
          setOutput(prev => prev + `[STATUS] ${message.data}\n`);
          break;
        case 'output':
          setOutput(prev => prev + message.data);
          break;
        case 'error':
          setOutput(prev => prev + `[ERROR] ${message.data}\n`);
          break;
        default:
          break;
      }
    };

    ws.onerror = (error) => {
      setOutput(prev => prev + `[ERROR] WebSocket error\n`);
      setIsExecuting(false);
    };

    ws.onclose = () => {
      setOutput(prev => prev + '\n--- Execution finished ---\n');
      setIsExecuting(false);
    };
  };

  const handleLanguageChange = (newLang) => {
    setLanguage(newLang);
    setCode(EXAMPLE_CODE[newLang]);
  };

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return (
    <div className="App">
      <header className="header">
        <h1>Code Execution Engine</h1>
        <div className="controls">
          <select 
            value={language} 
            onChange={(e) => handleLanguageChange(e.target.value)}
            disabled={isExecuting}
          >
            <option value="python">Python</option>
            <option value="cpp">C++</option>
            <option value="java">Java</option>
          </select>
          <button 
            onClick={executeCode}
            disabled={isExecuting}
            className="run-button"
          >
            {isExecuting ? 'Running...' : 'Run Code'}
          </button>
        </div>
      </header>

      <div className="container">
        <div className="editor-panel">
          <h3>Code Editor</h3>
          <Editor
            height="100%"
            language={language === 'cpp' ? 'cpp' : language}
            value={code}
            onChange={(value) => setCode(value || '')}
            theme="vs-dark"
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              scrollBeyondLastLine: false,
            }}
          />
        </div>

        <div className="output-panel">
          <h3>Output</h3>
          <pre className="output">{output || 'Output will appear here...'}</pre>
        </div>
      </div>
    </div>
  );
}

export default App;