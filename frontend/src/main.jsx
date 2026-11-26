import React from 'react';
import { createRoot } from 'react-dom/client';
import { ConfigProvider, theme } from 'antd';
import viVN from 'antd/locale/vi_VN';
import App from './App.jsx';
import './style.css';

createRoot(document.getElementById('root')).render(
  <ConfigProvider
    locale={viVN}
    theme={{
      algorithm: theme.darkAlgorithm,
      token: {
        colorPrimary: '#4c8dff',
        colorInfo: '#4c8dff',
        colorSuccess: '#2fbf8a',
        colorWarning: '#e0a43a',
        colorError: '#ef6670',
        colorBgBase: '#0b1220',
        colorBgContainer: '#121c31',
        colorBgElevated: '#172440',
        colorBorder: '#26354f',
        colorBorderSecondary: '#1f2c44',
        colorText: '#e3eaf5',
        colorTextSecondary: '#9aa9c2',
        borderRadius: 10,
        fontFamily: "'Nunito', system-ui, sans-serif",
      },
    }}
  >
    <App />
  </ConfigProvider>,
);
