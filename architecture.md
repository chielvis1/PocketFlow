# PocketFlow Architecture Diagrams

## System Architecture Overview

```mermaid
graph TB
    subgraph External["External Systems"]
        API[External APIs]
        DB[(Database)]
        Cache[(Cache)]
        Queue[(Message Queue)]
    end

    subgraph Core["Core System"]
        direction TB
        Input[Input Handler]
        Validator[Validator]
        Router[Operation Router]
        
        subgraph Processors["Processing Units"]
            direction LR
            Batch[Batch Processor]
            Single[Single Processor]
            Async[Async Processor]
        end
        
        Output[Output Handler]
        Monitor[Monitoring System]
    end

    subgraph LLM["LLM Integration"]
        PromptMgr[Prompt Manager]
        LLMClient[LLM Client]
        TokenCounter[Token Counter]
    end

    %% Core Flow
    Input --> Validator
    Validator --> Router
    Router --> Processors
    Processors --> Output
    
    %% Monitoring
    Router --> Monitor
    Processors --> Monitor
    Output --> Monitor
    
    %% External Interactions
    Input --> API
    Processors --> DB
    Processors --> Cache
    Async --> Queue
    
    %% LLM Integration
    Validator --> PromptMgr
    Processors --> LLMClient
    LLMClient --> TokenCounter
```

## Component Interactions

```mermaid
sequenceDiagram
    participant Client
    participant Input as Input Handler
    participant Validator
    participant Router
    participant Processor as Processor (Batch/Single/Async)
    participant LLM as LLM Service
    participant Output as Output Handler
    participant Monitor as Monitoring

    Client->>Input: Submit Request
    activate Input
    Input->>Validator: Validate Input
    activate Validator
    
    alt Valid Input
        Validator->>Router: Route Request
        activate Router
        Router->>Monitor: Log Operation Start
        Router->>Processor: Process Request
        activate Processor
        
        loop Processing
            Processor->>LLM: LLM Request
            LLM-->>Processor: LLM Response
            Processor->>Monitor: Update Progress
        end
        
        Processor->>Output: Handle Results
        deactivate Processor
        activate Output
        Output->>Monitor: Log Completion
        Output-->>Client: Return Results
        deactivate Output
    else Invalid Input
        Validator-->>Input: Return Error
        Input-->>Client: Error Response
    end
    
    deactivate Router
    deactivate Validator
    deactivate Input
```

## Batch Processing Flow

```mermaid
stateDiagram-v2
    [*] --> InputValidation
    
    state InputValidation {
        [*] --> Validating
        Validating --> Valid
        Validating --> Invalid
        Invalid --> Retry
        Retry --> Validating
        Valid --> [*]
    }
    
    state BatchProcessing {
        [*] --> Splitting
        Splitting --> SizeCheck
        
        state SizeCheck <<choice>>
        SizeCheck --> Processing: Size OK
        SizeCheck --> Adjusting: Too Large
        
        Adjusting --> Splitting
        
        state Processing {
            [*] --> InProgress
            InProgress --> Success
            InProgress --> Failed
            Failed --> Retry
            Retry --> InProgress
            Success --> [*]
        }
    }
    
    InputValidation --> BatchProcessing: Valid
    BatchProcessing --> ResultAggregation
    
    state ResultAggregation {
        [*] --> Combining
        Combining --> Validating
        Validating --> Success
        Validating --> Failed
        Failed --> Retry
        Retry --> Combining
        Success --> [*]
    }
    
    ResultAggregation --> [*]
```

## Async Processing Flow

```mermaid
stateDiagram-v2
    [*] --> QueueTask
    
    state QueueTask {
        [*] --> Queuing
        Queuing --> Queued
        Queuing --> Failed
        Failed --> Retry
        Retry --> Queuing
        Queued --> [*]
    }
    
    state MonitorProgress {
        [*] --> Checking
        Checking --> InProgress
        Checking --> TimedOut
        Checking --> Completed
        
        InProgress --> Checking: Wait
        TimedOut --> RetryDecision
        
        state RetryDecision <<choice>>
        RetryDecision --> QueueTask: Retry
        RetryDecision --> Failed: Max Retries
        
        Completed --> [*]
    }
    
    QueueTask --> MonitorProgress
    MonitorProgress --> CollectResults: Completed
    
    state CollectResults {
        [*] --> Collecting
        Collecting --> Validating
        Validating --> Valid
        Validating --> Invalid
        Invalid --> ErrorHandling
        Valid --> [*]
    }
    
    CollectResults --> [*]
```

## Error Handling Flow

```mermaid
stateDiagram-v2
    [*] --> ErrorDetection
    
    state ErrorDetection {
        [*] --> Analyzing
        Analyzing --> Categorizing
        Categorizing --> Recoverable
        Categorizing --> Fatal
    }
    
    state RecoveryAttempt {
        [*] --> Retry
        Retry --> Success
        Retry --> Failed
        Failed --> MaxRetries
        MaxRetries --> [*]
    }
    
    state Notification {
        [*] --> AlertGeneration
        AlertGeneration --> AdminNotification
        AlertGeneration --> LogError
        AdminNotification --> [*]
        LogError --> [*]
    }
    
    ErrorDetection --> RecoveryAttempt: Recoverable
    ErrorDetection --> Notification: Fatal
    RecoveryAttempt --> Notification: Max Retries
    RecoveryAttempt --> [*]: Success
    Notification --> [*]
```

## Monitoring and Metrics Flow

```mermaid
graph LR
    subgraph Collection["Metric Collection"]
        Performance[Performance Metrics]
        Resources[Resource Usage]
        Errors[Error Rates]
        Costs[Cost Tracking]
    end
    
    subgraph Processing["Metric Processing"]
        Aggregator[Metric Aggregator]
        Analyzer[Trend Analyzer]
    end
    
    subgraph Alerts["Alert System"]
        Threshold[Threshold Checker]
        Generator[Alert Generator]
        Notifier[Notification System]
    end
    
    Performance --> Aggregator
    Resources --> Aggregator
    Errors --> Aggregator
    Costs --> Aggregator
    
    Aggregator --> Analyzer
    Analyzer --> Threshold
    
    Threshold --> Generator
    Generator --> Notifier
``` 

## MCP Server Implementation Flow

```mermaid
flowchart TD
    RepoAnalysis[Repository Analysis] --> MCPPackager[MCP Packager]
    MCPPackager --> ImplGuides[Implementation Guides]
    ImplGuides --> ToolGen[Tool Generation]
    ToolGen --> ServerCreation[Server Creation]
    ServerCreation --> APIExposure[API Exposure]
    
    subgraph GuideGeneration["Implementation Guide Generation"]
        ExtractFeatures[Extract Features] --> CreateStructure[Create Guide Structure]
        CreateStructure --> GenerateConcepts[Generate Core Concepts]
        GenerateConcepts --> GenerateSteps[Generate Implementation Steps]
        GenerateSteps --> GenerateCode[Generate Code Examples]
    end
    
    subgraph ToolRegistration["Dynamic Tool Registration"]
        ParseFeatures[Parse Features] --> CreateTools[Create Tool Definitions]
        CreateTools --> RegisterTools[Register with Server]
        RegisterTools --> ValidateSchema[Validate Schemas]
    end
    
    ImplGuides --> GuideGeneration
    ToolGen --> ToolRegistration
    
    LLMService[LLM Service] -.-> GuideGeneration
```

### Implementation Guide Generation

**Purpose**: Creates structured AI-friendly implementation guides for repository features.

**Process Flow**:
1. **Extract Feature Details**: Parse repository analysis to identify key features
2. **Create Guide Structure**: Define structured JSON format for implementation guides
3. **Generate Core Concepts**: Identify fundamental principles behind each feature
4. **Map Implementation Steps**: Create step-by-step implementation instructions
5. **Define Class Structures**: Generate class definitions with attributes and methods
6. **Specify Method Details**: Define detailed method signatures with parameter descriptions
7. **Provide Integration Points**: Identify how features connect to the larger system

**Guide Components**:
- Core concepts and principles
- Dependencies and requirements
- Implementation steps with code examples
- Class and method specifications
- Integration points
- Testing approaches
- Agent-specific execution steps

**Feature-Specific Templates**:
- Flow implementation guides for orchestration features
- Node implementation guides for processing units
- Batch processing guides for parallel operations
- Utility function guides for helper components

### Tool Generation

**Purpose**: Creates MCP tool definitions from repository features and utilities.

**Process Flow**:
1. **Feature Extraction**: Extract features from repository analysis
2. **Tool Definition Creation**: Convert features to MCP tool definitions
3. **Schema Generation**: Create input/output schemas for each tool
4. **Documentation**: Generate comprehensive tool documentation
5. **Tool Registration**: Register tools with the MCP server

**Tool Categories**:
- Feature-specific tools for repository functionality
- Utility tools for common operations
- Implementation guide generators
- Repository exploration and navigation tools

**Tool Definition Structure**:
```
{
    "name": "tool_name",
    "description": "Comprehensive description",
    "inputSchema": {
        "type": "object",
        "properties": {...},
        "required": [...]
    },
    "outputSchema": {
        "type": "object",
        "properties": {...}
    }
}
```

### Server Creation

**Purpose**: Configures and initializes the MCP server with generated tools.

**Process Flow**:
1. **Server Initialization**: Create FastMCP server instance
2. **Base Tool Registration**: Register core tools for repository interaction
3. **Dynamic Tool Registration**: Register tools generated from repository analysis
4. **Configuration**: Set up server parameters (host, port, etc.)
5. **Error Handling**: Configure server-level error handling and logging

**Server Configuration Options**:
- Host and port settings
- Authentication options
- Rate limiting configuration
- Caching settings
- Logging and monitoring

**Dynamic Registration**:
The server dynamically registers tools based on repository analysis:
- Each feature in the repository becomes a tool
- Each utility function becomes a tool
- Implementation guides are exposed as tools
- Meta-tools for repository exploration are added

### API Exposure

**Purpose**: Exposes the MCP server through HTTP endpoints.

**Process Flow**:
1. **Endpoint Creation**: Define RESTful endpoints for tool access
2. **Documentation Generation**: Create OpenAPI specification
3. **Web Interface Setup**: Configure interactive documentation
4. **Authentication Layer**: Implement API key authentication
5. **Server Start**: Launch HTTP server on configured host/port

**Key Endpoints**:
- `/tools`: Lists all available tools
- `/tool/{tool_name}`: Executes a specific tool
- `/docs`: Interactive API documentation
- `/openapi.json`: OpenAPI specification
- `/status`: Server status and metrics

**Integration Patterns**:
- Direct HTTP API calls from external services
- Client library integration with language-specific SDKs
- Swagger UI for interactive testing
- AI agent integration through compatible clients 