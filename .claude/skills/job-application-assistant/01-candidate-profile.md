---
framework_version: 1.1.1
---

# Candidate Profile

<!-- SETUP: This file is populated by running /setup -->
<!-- After running /setup, all sections will be filled with your actual information -->

## Identity
- **Name:** Ridho Muhammad
- **Location:** West Java / Jakarta Metropolitan Area, Indonesia
- **Phone:** +6282186266734
- **Email:** rdhmuhammad57@gmail.com
- **LinkedIn:** https://www.linkedin.com/in/ridhomuhammad57
- **GitHub:** https://github.com/rdhmuhammad
- **Portfolio:** https://ridhoporto.my.id/
- **Medium:** https://medium.com/@5mblackburn7
- **Kaggle:** https://www.kaggle.com/ridhomuhammad
- **Status:** Employed (Backend Developer at ASLIRI, October 2023 - Present)
- **Constraints:** Open to Hybrid/On-site in Jakarta / Jabodetabek & West Java, other Indonesian tech hubs (Bandung, Yogyakarta, Bali), or Remote (Indonesia, APAC, Global).

### Languages
<!-- Every language you can work in professionally, with your honest level. Used by the
Language Gate in 04-job-evaluation.md and by job-scraper/search-queries.md's query-language
generation. Omit any language you don't actually work in - an undeclared language is treated as
a hard no, not a gap to smooth over. -->

| Language | Level | Notes |
|----------|-------|-------|
| Indonesian | Native or Bilingual | Extracted from LinkedIn profile |
| English | Professional Working | Extracted from LinkedIn profile |

## Education

| Degree | Period | Institution | Key Topics |
|--------|--------|-------------|------------|
| Bachelor of Computer Science (S1 Informatika) | Aug 2018 - Sep 2022 | Universitas Gunadarma | GPA: 3.32/4.00 (152 SKS). Algorithms & Programming, Object-Oriented Programming, Algorithm Design & Analysis, Database Systems, Operating Systems, Computer Security, IT Forensics, Big Data Computing, Web Programming, Software Project Management, Image Processing, Compiler Techniques, Artificial Intelligence, Deep Learning |
| Industry Project Exploration (IPE) Bootcamp | Aug 2021 - Feb 2022 | Glints Academy | Project-based backend engineering bootcamp; collaborated across backend, frontend, and mobile teams to build an industrial application for client LingoTalk |
| Machine Learning Path Participant | Jan 2021 - Aug 2021 | Bangkit Academy (Google, Tokopedia, Gojek, Traveloka) | Built a Sign Language Translator mobile capstone project with 4 teammates (dataset creation, architecture, training via TensorFlow Object Detection API); completed 5 Coursera specializations |

### Certifications
- **TensorFlow: Data and Deployment Specialization** — Coursera / DeepLearning.AI
- **Structuring Machine Learning Projects** — Coursera / DeepLearning.AI
- **Google IT Automation Professional Certificate** — Coursera / Google
- **Google IT Support Professional Certificate** — Coursera / Google

## Professional Experience

### Backend Developer - ASLIRI (October 2023 - Present)
Jakarta, Indonesia
- Developed backend systems in a complex, high-traffic, near-zero-downtime environment leveraging Spring Boot (Java), Kafka, RabbitMQ, PostgreSQL, and Docker, with hardware/IoT communication via MQTT, WebSocket (STOMP), RTSP streaming/FFmpeg, and Firebase notifications.
- Contributed to the development of confidential public-security and investigation products for high-level government agencies, including Facial Recognition (FR), Automatic Number Plate Recognition (ANPR), building access control, and smart parking systems, passing regular external penetration testing and security certifications.
- Engineered autonomous agentic workflows with Large Language Models (LLMs), Model Context Protocol (MCP), custom agent tools, and Retrieval-Augmented Generation (RAG) powered by Qdrant vector storage.
- Took initiative to maintain and enhance core backend utilities during spare time, including base repository structures, Spring Security setup, and foundational Face Recognition (FR) engine implementations.
- Engaged directly with end-users in the field to gather feedback, support on-site implementation, and ensure smooth system operation.

### Backend Developer - Moladin (April 2022 - October 2023)
South Jakarta, Jakarta, Indonesia
- Developed backend applications in Golang and Node.js using Hexagonal Architecture for the Moladin Car Center (MCC) app and CRM across branches in Sumatra and Java (supporting transaction oversight, inventory management, financing integration, and anti-fraud workflows), operating across monolithic services and event-driven inter-service communication via Kafka and HTTP calls.
- Maintained ~90% unit test coverage across repository, use-case, controller, and request-handler layers using table-driven tests.
- Produced comprehensive technical documentation, including API contracts, Technical Specifications, and Release plans, collaborating closely with Product, Design, and QA teams through Focus Group Discussions and iterative prototyping.
- Actively participated in an On-Call rotation to promptly resolve production incidents within agreed Service Level Agreements (SLAs).

## Independent Projects
<!-- Projects outside of employment: freelance, open source, personal -->
- **API Tester (`apitester-desktop` & `apitester-generator-spring`)** (Apr 2025 - Present | [GitHub](https://github.com/rdhmuhammad/apitester)): Built an integrated API testing and documentation ecosystem comprising: (1) a Spring Boot starter (`apitester-generator-spring`, Java 11+) that introspects REST controllers and DTOs at startup to auto-generate Postman v2.1 collections, serves an embedded React Web UI (`/apitester`) with Cookie-JWT auth, and executes a non-destructive RFC 6902 (`zjsonpatch`) Three-Way Collection Merge using deterministic UUIDv3/v5 seeding (`Controller#method`) and Flatten-Diff-Merge-Unflatten to preserve developer edits across rebuilds; and (2) a desktop client built with Go 1.26 (Gin, Socket.IO, embedded BoltDB `bbolt`), Electron 35, React 19, TypeScript, Redux Toolkit, and TanStack Query featuring multi-tab request editing, pre/post-request JS scripting sandbox, `{{variable}}` and mock data resolution, `.http` scenario runner, Ansible playbook editor, SHA-256 `collection_history` mutation auditing, Windows Service packaging + Inno Setup installer, and a Playwright E2E test suite with cumulative caching and Google Drive XLSX report synchronization.
- **Phisio.book.app (PhysioBook)** (Apr 2026 - Present | [Live App](https://phisiobook.vercel.app/)): Developed the Golang backend and receptionist administrative dashboard for a physiotherapy clinic group operating across Bali and Jakarta (500+ therapists, 50+ cities), replacing manual WhatsApp coordination with online session scheduling, pre-appointment real-time doctor chat, secure medical check-up document downloads, monitored payment workflows, and monthly clinic revenue reporting.
- **Bestcuci.id** (Jul 2025 - Feb 2026 | [Live Web](https://bestcuci.id/)): Designed and built a Golang backend and multi-role web platform (customer mobile web app, driver app, owner dashboard) to modernize local laundry pickup, delivery, and bookkeeping; engineered for 200+ daily orders on low-cost VPS infrastructure using Golang, MySQL, MongoDB, Redis, MinIO, Google Maps API, Nginx, and Cloudflare, with rich structured logging and operational priority-handling tools.
- **Miragi (`miragiapp.com`)** (Jul 2025 - Dec 2025): Developed the Golang backend for a Bali tourist destination discovery platform supporting a mobile app and admin CMS with multi-language AI voice narration via ElevenLabs; solved parallel voice-generation bottlenecks using Go's concurrency model, structured logging, persistent failure storage, and an admin-triggered retry mechanism.
- **Go Skeleton (`base-be-golang`)** (Jan 2024 - Mar 2024 | [GitHub](https://github.com/rdhmuhammad/base-be-golang)): Built a reusable Golang backend skeleton using Gin, GORM, MongoDB/MySQL, Redis, MinIO, and Sentry with decoupled business logic, data persistence, and adapter layers, generic repository methods to eliminate CRUD boilerplate, and a reusable IAM module.
- **BRI BFLP Backend Engineering Bootcamp Mentorship (via dibimbing.id)** (May 2023 - Jul 2023 | Certificate `NMNTR29050005`): Appointed as Backend Trainer (Golang stack) for Bank Rakyat Indonesia's 30-hour B2B bootcamp preparing engineers for the BRI BFLP program; taught backend classes, mentored final projects, evaluated student technical reports, and presented final performance assessments.
- **Kassir Bersih & Rebirth AkuCuci.in** (2023 | [Architecture Diagrams](https://github.com/rdhmuhammad/delivery-laundry-diagram)): Formulated technical specifications, ERDs/UMLs, Postman API contracts, and Golang backend services (deployed on GCP with Sentry monitoring) for a multi-outlet laundry Point-of-Sale SaaS (`Kassir Bersih`) and a high-volume laundry delivery platform (`AkuCuci.in`, architected for ~1,000 active users and ~90,000 transactions with caching, concurrency, and Google Maps delivery-cost calculation).
- **Technical Writing & Open Datasets ([Medium](https://medium.com/@5mblackburn7) & [Kaggle](https://www.kaggle.com/ridhomuhammad))**: Published backend engineering articles on Medium covering Advanced & Basic Java Validation Patterns, HMAC-based OTP (HOTP) in Go, MySQL remote VPS security, and Docker concepts; published the SIBI Sign Language Object Detection dataset and notebooks for SSD v1 Object Detection and WhatsApp Chatbot Text Classification on Kaggle.

## Technical Skills

### Programming & Backend Frameworks
- **Golang** (Primary / Advanced): Gin, GORM, Socket.IO, BoltDB (`bbolt`), Go concurrency patterns, table-driven unit testing
- **Java** (Primary / Advanced): Spring Boot, Spring Security, Jackson, `zjsonpatch`, Gradle, Maven, JasperReports
- **TypeScript / JavaScript** (Intermediate): Node.js, React 19, Vite, Electron, Redux Toolkit, TanStack Query, Tailwind CSS, Playwright
- **Python** (Working knowledge): TensorFlow Object Detection API, OpenCV, text classification & computer vision pipelines

### AI, Computer Vision & Real-Time Streaming
- **Agentic AI & LLMs**: Autonomous agent workflows, Model Context Protocol (MCP) servers & custom agent tools, Retrieval-Augmented Generation (RAG), Qdrant vector database, ElevenLabs TTS API
- **Computer Vision & IoT / Media**: Facial Recognition (FR) integration, Automatic Number Plate Recognition (ANPR), RTSP video streaming, FFmpeg, MQTT hardware communication, WebSocket (STOMP & Socket.IO), Firebase Cloud Messaging

### Databases, Messaging & Infrastructure
- **Databases & Storage**: PostgreSQL, MySQL, MongoDB, Redis, BoltDB (`bbolt`), Qdrant, MinIO Object Storage
- **Messaging & Event-Driven**: Apache Kafka, RabbitMQ
- **DevOps, Auth & Tooling**: Docker, Nginx, Cloudflare, Linux VPS, Google Cloud Platform (GCP), Ansible, Keycloak (IAM), JWT / HttpOnly Cookie Auth, Google Maps API, Sentry, Postman, Git, Inno Setup

### Domain Expertise
- Public Security, Biometrics (Face Recognition / ANPR), Smart Parking & Building Access Control Systems
- Developer Tooling, API Documentation Generation & Automated Testing Platforms
- E-Commerce, Automotive Marketplace & On-Demand Logistics / Booking Platforms (POS, Clinic Scheduling, Delivery Routing)

## Publications
<!-- List peer-reviewed publications, if any -->
1. Ridho Muhammad (2022). *Face Recognition using Cascade Classifier, Haar Selection OpenCV*.

## Awards
- **Remarkable Mentor Certificate (`NMNTR29050005`)** - Bootcamp For Company (B2B) at Dibimbing.id / Bank Rakyat Indonesia (May 2023)

## References
Available upon request.
