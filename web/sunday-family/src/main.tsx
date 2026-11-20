import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles.css';
import { InstallPrompt } from './InstallPrompt';
import { registerServiceWorker } from './pwa';

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);

createRoot(document.getElementById('install')!).render(<StrictMode><InstallPrompt /></StrictMode>);
void registerServiceWorker();
