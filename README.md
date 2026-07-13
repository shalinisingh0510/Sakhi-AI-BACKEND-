# 🌸 Sakhi AI – Backend Development Master Prompt

## Project Overview

You are building the backend of **Sakhi AI**, an AI-powered multilingual women's health education platform designed to educate, support, and empower girls and women with trusted, culturally sensitive, and scientifically accurate health information.

The backend is responsible for powering the entire platform by managing authentication, AI conversations, user progress, multilingual content, health education modules, notifications, and secure data management.

The primary goal is to build a secure, scalable, maintainable, and production-ready backend that enables a safe and reliable learning experience.

---

# Vision

Create a reliable backend infrastructure that allows every girl and woman to access trusted health education anytime, anywhere, in their preferred language.

The backend should be designed for long-term scalability, security, and seamless AI integration.

---

# Mission

Develop a robust backend system that securely manages users, AI-powered conversations, educational content, multilingual support, analytics, and future healthcare integrations while maintaining high performance and reliability.

---

# Target Users

The backend should support:

- Girls (10–13 years)
- Teenagers (14–18 years)
- Women (18+)
- Mothers
- Caregivers
- Administrators
- Content Managers
- Future Healthcare Professionals

---

# Backend Goal

Develop a modular, scalable, secure, and maintainable REST API architecture that supports the frontend efficiently and provides reliable services for all platform features.

The backend should prioritize:

- Security
- Performance
- Scalability
- Maintainability
- Reliability

---

# System Responsibilities

The backend should manage:

- User Authentication
- User Authorization
- User Profiles
- AI Conversations
- Educational Lessons
- Voice Interaction
- Learning Progress
- Notifications
- Health Tracking
- Language Preferences
- Analytics
- Admin Dashboard APIs
- Content Management
- Future Doctor Integration

---

# Backend Architecture

Use a clean and modular architecture.

Suggested technologies:

- Node.js
- Express.js
- TypeScript
- MongoDB
- Mongoose
- Redis (Caching)
- JWT Authentication
- REST API
- OpenAI API (or configurable AI provider)
- Cloud Storage (for future media support)

Organize code into reusable modules.

---

# Folder Organization

Maintain a scalable folder structure.

Example modules:

- Authentication
- Users
- AI
- Lessons
- Progress
- Notifications
- Languages
- Analytics
- Admin
- Middleware
- Utilities
- Configuration
- Database
- Services

Each module should be independent and maintainable.

---

# API Design Principles

Every API should be:

- RESTful
- Predictable
- Versioned
- Secure
- Well documented
- Consistent

Use meaningful endpoint names and standard HTTP status codes.

---

# Authentication

Implement secure authentication using:

- JWT Access Tokens
- Refresh Tokens
- Password Hashing (bcrypt)
- Role-Based Access Control (RBAC)

Supported Roles:

- User
- Admin
- Moderator (Future)

Never store plain-text passwords.

---

# Database Design

The database should be designed with scalability in mind.

Suggested collections:

- Users
- Conversations
- Lessons
- Categories
- Progress
- Notifications
- Languages
- Feedback
- Analytics
- Admin Logs

Relationships should remain simple, consistent, and optimized.

---

# AI Integration

The AI service should:

- Generate trusted educational responses
- Maintain conversational context
- Support multilingual communication
- Avoid harmful or misleading medical advice
- Clearly distinguish educational information from professional medical consultation

The backend should allow switching AI providers without affecting other modules.

---

# Multilingual Support

Support multiple languages including:

- English
- Hindi
- Bengali
- Marathi
- Tamil
- Telugu
- Kannada
- Gujarati
- Punjabi
- Odia

Language selection should be stored per user.

Avoid hardcoded strings where localization is required.

---

# Security Principles

Prioritize user privacy and security.

Implement:

- HTTPS
- JWT Validation
- Input Validation
- Request Sanitization
- Rate Limiting
- CORS
- Helmet
- Secure Environment Variables
- Password Hashing
- API Authentication
- Role Authorization

Never expose sensitive information through APIs.

---

# Error Handling

All APIs should return standardized responses.

Include:

- Success Status
- Error Status
- Clear Error Messages
- Validation Errors
- HTTP Status Codes

Avoid exposing internal server details.

---

# Performance Optimization

Optimize backend performance by:

- Database Indexing
- Pagination
- Lazy Loading
- Redis Caching
- Efficient Queries
- Compression
- Connection Pooling

Minimize unnecessary database requests.

---

# Logging & Monitoring

Implement structured logging.

Log:

- Authentication Events
- Errors
- API Requests
- AI Requests
- System Warnings

Prepare the application for future monitoring tools.

---

# Testing

Ensure code quality through:

- Unit Testing
- Integration Testing
- API Testing

Maintain reliable and predictable backend behavior.

---

# Scalability

Design the backend to support:

- Millions of users
- AI service upgrades
- Additional languages
- Mobile applications
- Future healthcare integrations
- New learning modules
- Cloud deployment

Avoid tightly coupled code.

---

# Future Features

Backend should be designed to support:

- Video Lessons
- Voice Assistant
- AI Health Educator
- Wearable Integration
- Doctor Consultation
- Community Support
- Appointment Booking
- Personalized Learning Paths
- Recommendation Engine

Architecture should remain extensible.

---

# Development Guidelines

Always:

- Write clean code
- Follow SOLID principles
- Keep business logic separate from routes
- Validate all inputs
- Reuse services
- Avoid duplicate code
- Use environment variables
- Document APIs
- Keep modules independent

---

# AI Development Rules

While generating backend code:

- Follow modular architecture.
- Write reusable services.
- Keep APIs RESTful.
- Prioritize security.
- Maintain scalability.
- Separate controllers, services, models, and routes.
- Use proper validation.
- Write production-ready code.
- Follow consistent naming conventions.
- Document important logic with concise comments.

---

# Project Philosophy

Sakhi AI is more than a backend service.

It is the foundation of a trusted educational platform that empowers girls and women with accurate health knowledge, multilingual accessibility, privacy, and compassionate AI guidance.

Every backend decision should reinforce reliability, security, empathy, and long-term scalability.

The backend should always prioritize user trust, data protection, and maintainable engineering practices.