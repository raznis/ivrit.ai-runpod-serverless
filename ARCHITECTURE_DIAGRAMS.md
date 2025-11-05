# Scribe Rabbit Architecture Diagrams

## Overview Architecture

This document contains architecture diagrams for the Scribe Rabbit transcription service.

## Current Implementation - FastAPI Deployment

```mermaid
flowchart TB
    subgraph ClientEnv["Client Environment"]
        direction TB
        Client["Client Applications<br/>(Web/Mobile/API)"]

        subgraph Deployment["Scribe Rabbit Deployment<br/>(AWS/GCP Private Cloud)"]
            direction TB
            
            subgraph API["API Layer"]
                LoadBalancer["Load Balancer<br/>(ALB/Cloud LB)"]
                APIService["FastAPI Service<br/>(Auto-scaling)"]
            end
            
            Queue["Job Manager<br/>(Redis + Celery)"]
            
            subgraph Core["Core Logic - Workers"]
                direction TB
                Transcribe["ASR Worker<br/>(Whisper Models)<br/>GPU-enabled"]
                Separate["Post Processing<br/>(Diarization)"]
            end
            
            subgraph EnhancedAI["Enhanced_AI (Future)"]
                direction TB
                EnhancedProcessor["Enhanced AI Service<br/>(Placeholder)"]
                LLMProcessor["LLM Processing<br/>(Summarization, etc)"]
            end
            
            DB["Internal DB<br/>(PostgreSQL)"]
            Storage["Object Storage<br/>(S3/Cloud Storage)"]
        end
    end

    OpenAI["External LLM Service<br/>(OpenAI/Custom)"]

    subgraph ScribeRabbit["Scribe Rabbit Cloud"]
        Metrics["Usage and Health Metrics<br/>Dashboard<br/>(Prometheus/CloudWatch)"]
    end

    %% Data flow
    Client <-->|"REST API<br/>Webhooks"| LoadBalancer
    LoadBalancer --> APIService
    APIService -->|"Submit Job"| Queue
    APIService <-->|"Job Status<br/>Results"| DB
    APIService <-->|"Store/Retrieve<br/>Audio Files"| Storage
    
    Queue -->|"Process Job"| Transcribe
    Transcribe --> Separate
    Separate -->|"Job Complete"| DB
    
    %% Enhanced AI flow (placeholder)
    DB -.->|"Transcription<br/>Result"| EnhancedProcessor
    EnhancedProcessor -.-> LLMProcessor
    LLMProcessor -.->|"Enhanced<br/>Result"| DB

    %% External LLM call (future)
    LLMProcessor -.->|"HTTPS API call"| OpenAI
    
    %% Telemetry
    APIService --> Metrics
    Queue --> Metrics
    Transcribe --> Metrics

    %% Styling
    classDef implemented fill:#90EE90,stroke:#333,stroke-width:2px
    classDef placeholder fill:#FFE4B5,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    classDef external fill:#87CEEB,stroke:#333,stroke-width:2px
    
    class Client,LoadBalancer,APIService,Queue,Transcribe,Separate,DB,Storage,Metrics implemented
    class EnhancedProcessor,LLMProcessor placeholder
    class OpenAI external
```

**Legend:**
- 🟢 Green boxes: Fully implemented
- 🟡 Orange dashed boxes: Placeholder for future Enhanced_AI integration
- 🔵 Blue boxes: External services

---

## Detailed Component Architecture

```mermaid
flowchart LR
    subgraph Client["Client Layer"]
        WebApp["Web Application"]
        MobileApp["Mobile App"]
        APIClient["API Integration"]
    end

    subgraph CloudInfra["Cloud Infrastructure (AWS/GCP)"]
        subgraph Network["Network Layer"]
            LB["Load Balancer<br/>SSL/TLS Termination"]
            CDN["CDN<br/>(Optional)"]
        end

        subgraph Compute["Compute Layer"]
            subgraph APITier["API Tier<br/>(Stateless)"]
                API1["FastAPI<br/>Instance 1"]
                API2["FastAPI<br/>Instance 2"]
                API3["FastAPI<br/>Instance N"]
            end

            subgraph WorkerTier["Worker Tier<br/>(GPU-enabled)"]
                Worker1["Celery Worker 1<br/>+ GPU (T4/A100)"]
                Worker2["Celery Worker 2<br/>+ GPU (T4/A100)"]
                Worker3["Celery Worker N<br/>+ GPU (T4/A100)"]
            end
        end

        subgraph Data["Data Layer"]
            PostgreSQL["PostgreSQL<br/>(RDS/Cloud SQL)<br/>Jobs & Metadata"]
            Redis["Redis<br/>(ElastiCache/Memorystore)<br/>Task Queue"]
            S3["Object Storage<br/>(S3/Cloud Storage)<br/>Audio Files"]
        end

        subgraph Monitoring["Observability"]
            Prometheus["Metrics<br/>(Prometheus)"]
            Logs["Logs<br/>(CloudWatch/Cloud Logging)"]
            Alerts["Alerts<br/>(PagerDuty/Slack)"]
        end
    end

    subgraph External["External Services"]
        Webhooks["Client Webhooks"]
        EnhancedAIExt["Enhanced_AI Service<br/>(Future)"]
    end

    %% Connections
    Client --> LB
    LB --> APITier
    APITier <--> PostgreSQL
    APITier <--> Redis
    APITier <--> S3
    
    Redis --> WorkerTier
    WorkerTier <--> PostgreSQL
    WorkerTier <--> S3
    
    APITier --> Webhooks
    WorkerTier --> Webhooks
    
    APITier --> Prometheus
    WorkerTier --> Prometheus
    APITier --> Logs
    WorkerTier --> Logs
    
    Prometheus --> Alerts
    Logs --> Alerts
    
    WorkerTier -.-> EnhancedAIExt

    classDef apiStyle fill:#4A90E2,stroke:#333,stroke-width:2px,color:#fff
    classDef workerStyle fill:#E27D60,stroke:#333,stroke-width:2px,color:#fff
    classDef dataStyle fill:#85DCBA,stroke:#333,stroke-width:2px
    classDef monitorStyle fill:#C38D9E,stroke:#333,stroke-width:2px,color:#fff
    
    class API1,API2,API3 apiStyle
    class Worker1,Worker2,Worker3 workerStyle
    class PostgreSQL,Redis,S3 dataStyle
    class Prometheus,Logs,Alerts monitorStyle
```

---

## Job Processing Flow

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI Service
    participant DB as PostgreSQL
    participant Queue as Redis/Celery
    participant Worker as GPU Worker
    participant Storage as S3/Cloud Storage
    participant Webhook as Client Webhook

    Client->>API: POST /api/v1/transcribe<br/>{url, model, options}
    API->>API: Validate request<br/>Check API key
    API->>DB: Create job record<br/>Status: PENDING
    DB-->>API: Job ID
    API->>Queue: Submit task to queue<br/>{job_id, params}
    API-->>Client: 202 Accepted<br/>{job_id, status: "pending"}
    
    Note over Queue,Worker: Async Processing
    
    Queue->>Worker: Assign task
    Worker->>DB: Update status: PROCESSING
    Worker->>Webhook: POST {status: "transcribing"}
    
    Worker->>Worker: Load Whisper model<br/>(cached if available)
    Worker->>Storage: Download audio file<br/>(if URL provided)
    Worker->>Worker: Perform transcription<br/>GPU inference
    Worker->>Worker: Apply diarization<br/>(if requested)
    
    Worker->>DB: Update with results<br/>Status: COMPLETED
    Worker->>Webhook: POST {status: "transcribed",<br/>transcription: "..."}
    
    Client->>API: GET /api/v1/jobs/{job_id}
    API->>DB: Fetch job details
    DB-->>API: Job data + results
    API-->>Client: 200 OK<br/>{status: "completed",<br/>result: {...}}
    
    Note over Client,Worker: Optional: Enhanced_AI Step
    
    Client->>API: POST /api/v1/enhanced-ai<br/>{transcription_job_id}
    API->>DB: Create Enhanced_AI job
    API->>Queue: Submit Enhanced_AI task<br/>(placeholder)
    API-->>Client: 202 Accepted<br/>{enhanced_job_id}
```

---

## AWS Deployment Architecture

```mermaid
flowchart TB
    subgraph Internet
        Users["Users/Clients"]
    end

    subgraph AWS["AWS Cloud"]
        subgraph VPC["VPC"]
            subgraph PublicSubnet["Public Subnet"]
                ALB["Application<br/>Load Balancer"]
            end

            subgraph PrivateSubnet1["Private Subnet 1"]
                Fargate["ECS Fargate<br/>FastAPI Service<br/>(Auto-scaling)"]
            end

            subgraph PrivateSubnet2["Private Subnet 2"]
                ECS["ECS on EC2<br/>GPU Workers<br/>(g4dn instances)"]
            end

            subgraph DataSubnet["Data Subnet"]
                RDS["RDS PostgreSQL<br/>(Multi-AZ)"]
                ElastiCache["ElastiCache<br/>Redis"]
            end
        end

        S3["S3 Bucket<br/>Audio Storage"]
        ECR["ECR<br/>Container Registry"]
        Secrets["Secrets Manager<br/>API Keys & Credentials"]
        CloudWatch["CloudWatch<br/>Logs & Metrics"]
    end

    Users --> ALB
    ALB --> Fargate
    Fargate <--> RDS
    Fargate <--> ElastiCache
    Fargate <--> S3
    Fargate --> CloudWatch
    
    ElastiCache --> ECS
    ECS <--> RDS
    ECS <--> S3
    ECS --> CloudWatch
    
    Fargate -.-> Secrets
    ECS -.-> Secrets
    
    Fargate -.-> ECR
    ECS -.-> ECR

    classDef awsCompute fill:#FF9900,stroke:#333,stroke-width:2px,color:#fff
    classDef awsStorage fill:#569A31,stroke:#333,stroke-width:2px,color:#fff
    classDef awsNetwork fill:#8B4513,stroke:#333,stroke-width:2px,color:#fff
    
    class Fargate,ECS awsCompute
    class RDS,ElastiCache,S3,ECR awsStorage
    class ALB,VPC awsNetwork
```

---

## GCP Deployment Architecture

```mermaid
flowchart TB
    subgraph Internet
        Users["Users/Clients"]
    end

    subgraph GCP["Google Cloud Platform"]
        subgraph Network["VPC Network"]
            CLB["Cloud Load<br/>Balancer"]
            
            subgraph CloudRun["Cloud Run"]
                API["FastAPI Service<br/>(Auto-scaling)"]
            end

            subgraph GKE["GKE Cluster"]
                subgraph GPUPool["GPU Node Pool"]
                    Worker1["Worker Pod 1<br/>+ T4 GPU"]
                    Worker2["Worker Pod 2<br/>+ T4 GPU"]
                end
            end
        end

        CloudSQL["Cloud SQL<br/>PostgreSQL"]
        Memorystore["Memorystore<br/>Redis"]
        GCS["Cloud Storage<br/>Audio Bucket"]
        GCR["Container Registry<br/>Docker Images"]
        SecretManager["Secret Manager<br/>Credentials"]
        CloudMonitoring["Cloud Monitoring<br/>& Logging"]
    end

    Users --> CLB
    CLB --> API
    API <--> CloudSQL
    API <--> Memorystore
    API <--> GCS
    API --> CloudMonitoring
    
    Memorystore --> GPUPool
    Worker1 <--> CloudSQL
    Worker2 <--> CloudSQL
    Worker1 <--> GCS
    Worker2 <--> GCS
    GPUPool --> CloudMonitoring
    
    API -.-> SecretManager
    GPUPool -.-> SecretManager
    
    API -.-> GCR
    GPUPool -.-> GCR

    classDef gcpCompute fill:#4285F4,stroke:#333,stroke-width:2px,color:#fff
    classDef gcpStorage fill:#34A853,stroke:#333,stroke-width:2px,color:#fff
    classDef gcpNetwork fill:#EA4335,stroke:#333,stroke-width:2px,color:#fff
    
    class API,GPUPool gcpCompute
    class CloudSQL,Memorystore,GCS,GCR gcpStorage
    class CLB,Network gcpNetwork
```

---

## Enhanced_AI Integration (Future State)

```mermaid
flowchart TB
    subgraph Current["Current Implementation"]
        AudioIn["Audio Input"]
        Transcription["Transcription Service<br/>(Whisper + Diarization)"]
        TranscriptOut["Transcription Output<br/>{text, segments, speakers}"]
    end

    subgraph Future["Enhanced_AI Integration (Placeholder)"]
        direction TB
        
        subgraph Processing["Enhanced Processing Pipeline"]
            Summarization["Summarization<br/>(Extract key points)"]
            EntityExtraction["Entity Extraction<br/>(Names, dates, places)"]
            SentimentAnalysis["Sentiment Analysis<br/>(Tone, emotion)"]
            KeywordExtraction["Keyword Extraction<br/>(Important terms)"]
        end

        subgraph LLM["LLM Services"]
            GPT["OpenAI GPT-4"]
            Claude["Anthropic Claude"]
            Custom["Custom Model"]
        end

        EnhancedOut["Enhanced Output<br/>{summary, entities,<br/>sentiment, keywords}"]
    end

    AudioIn --> Transcription
    Transcription --> TranscriptOut
    
    TranscriptOut -.->|"POST /api/v1/enhanced-ai"| Processing
    
    Processing --> LLM
    LLM --> EnhancedOut

    classDef implemented fill:#90EE90,stroke:#333,stroke-width:2px
    classDef placeholder fill:#FFE4B5,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    
    class AudioIn,Transcription,TranscriptOut implemented
    class Processing,LLM,EnhancedOut placeholder
```

---

## Notes

1. **Green solid boxes** indicate fully implemented components
2. **Orange dashed boxes** indicate placeholder components for Enhanced_AI integration
3. **Blue boxes** indicate external services
4. All diagrams reflect the current FastAPI-based architecture suitable for AWS or GCP deployment
5. The Enhanced_AI integration is designed but not yet implemented, providing a clear path for future development

## Quick Reference

- **API Documentation**: Available at `/docs` when service is running
- **Health Check**: `GET /health`
- **Metrics**: `GET /metrics` (Prometheus format)
- **Job Status**: `GET /api/v1/jobs/{job_id}`
