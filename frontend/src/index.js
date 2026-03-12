import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { applySavedAccent } from './theme';

// Apply theme and accent immediately to prevent flash
const savedTheme = localStorage.getItem('app_theme') || 'dark';
document.documentElement.setAttribute('data-theme', savedTheme);
applySavedAccent();

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

