# Career OS Frontend

This is a Next.js (TypeScript) web application that serves as the primary GUI for Career OS.
It features a dark mode, glassmorphism, and live activity streams via WebSockets.

## Setup Instructions (On Target Machine)

Since dependencies were not installed locally to respect machine constraints, follow these steps to get the frontend running:

1. Install Node.js dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Run the development server:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Environment Variables
- `.env.development`: Used when running `npm run dev`
- `.env.production`: Used when running `npm run build && npm start`
