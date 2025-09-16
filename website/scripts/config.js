const config = {
  BACKEND_URL: process.env.BACKEND_URL || 'http://localhost:8000',
  WEBSOCKET_URL: process.env.WEBSOCKET_URL || 'ws://localhost:8000/ws',
};
export default config;
