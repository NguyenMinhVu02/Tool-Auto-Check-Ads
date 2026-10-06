import React from 'react';
import { createRoot } from 'react-dom/client';
import { ConfigProvider } from 'antd';
import viVN from 'antd/locale/vi_VN';
import App from './App.jsx';
import './style.css';

createRoot(document.getElementById('root')).render(
  <ConfigProvider
    locale={viVN}
    theme={{
      token: {
        colorPrimary: '#2767d8',
        colorInfo: '#2767d8',
        colorSuccess: '#19956d',
        colorWarning: '#cf8e21',
        colorError: '#d14c55',
        borderRadius: 10,
        fontFamily: 'Poppins, sans-serif',
      },
    }}
  >
    <App />
  </ConfigProvider>,
);
