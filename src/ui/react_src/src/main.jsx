import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    this.setState({ error, errorInfo });
    console.error('[CosmoLights UI Error]', error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: '#120407',
          color: '#ff6b81',
          padding: '28px',
          fontFamily: 'monospace',
          fontSize: '13px',
          overflow: 'auto',
          zIndex: 999999,
          whiteSpace: 'pre-wrap',
        }}>
          <h2 style={{ color: '#ff4757', margin: '0 0 12px 0', fontSize: '18px' }}>
            ⚠️ Error de Renderizado en CosmoLights UI
          </h2>
          <div style={{ color: '#fff', marginBottom: '12px' }}>
            <strong>Mensaje:</strong> {String(this.state.error?.message || this.state.error)}
          </div>
          <div style={{ color: '#aaa', marginBottom: '8px' }}>Pila de ejecución (Stack):</div>
          <pre style={{ background: '#20080d', padding: '14px', borderRadius: '8px', color: '#ffb8b8', overflowX: 'auto' }}>
            {this.state.error?.stack}
          </pre>
          <div style={{ color: '#aaa', margin: '12px 0 8px 0' }}>Componente:</div>
          <pre style={{ background: '#20080d', padding: '14px', borderRadius: '8px', color: '#e0e0e0', overflowX: 'auto' }}>
            {this.state.errorInfo?.componentStack}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}
