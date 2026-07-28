# Strafwecker Project Guide

## Prerequisites

- There is a folder called flask-server, it contains a copy of the flask server that is running on the raspberry pi. Just so you know how it works and how exactly the endpoints work, and how they deliver the data.

## Build Commands

- `npm run dev` - Start development server
- `npm run build` - Build production version
- `npm run start` - Start production server
- `npm run lint` - Run ESLint on codebase

## Code Style Guidelines

- Use strict TypeScript with proper interfaces for all objects (e.g., `Alarm`, `Log`)
- Components: Follow React functional component style with proper typing
- Imports: Group in sections - React, components, hooks, utils, types
- State Management: Use React hooks (useState, useEffect) for component state
- Error Handling: Use try/catch with proper logging and toast notifications
- API Calls: Handle all errors, set loading state before/after requests
- Naming: Use camelCase for variables/functions, PascalCase for components
- CSS: Use Tailwind utility classes with cn() helper for conditional classes
- Mobile-first design with responsive considerations
- Dark theme as default for mobile devices

## Formatting

- TypeScript strict mode enabled
- Follow established patterns in existing components
