# AnimationCreator SaaS - Web Application Plan

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│  Next.js 14 + TypeScript + Tailwind + Shadcn/UI                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  Auth    │ │ Creator  │ │ Gallery  │ │ Billing  │           │
│  │  Pages   │ │  Studio  │ │   View   │ │  Portal  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │ API
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND                                  │
│  FastAPI + Python                                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  Auth    │ │Generation│ │  Credits │ │  Assets  │           │
│  │ Service  │ │  Queue   │ │  System  │ │ Storage  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      INFRASTRUCTURE                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Supabase │ │   S3/    │ │  Redis   │ │  Stripe  │           │
│  │ Postgres │ │ Cloudfl. │ │  Queue   │ │ Payments │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Workstreams (Parallel Agent Tasks)

Each workstream is **independent** and can be developed in parallel. They communicate via defined interfaces.

---

## WORKSTREAM 1: Database & Auth
**Agent Focus**: Database schema, authentication, user management

### Tasks
```
1.1 Database Schema (Supabase/Postgres)
    ├── users (id, email, name, avatar, created_at)
    ├── credits (user_id, balance, lifetime_purchased)
    ├── transactions (id, user_id, type, amount, stripe_id, created_at)
    ├── characters (id, user_id, prompt, style, image_url, created_at)
    ├── animations (id, character_id, state, video_url, gif_url, status)
    └── generations (id, user_id, credits_used, started_at, completed_at)

1.2 Authentication
    ├── Supabase Auth integration
    ├── OAuth providers (Google, GitHub, Discord)
    ├── Session management
    └── Protected API routes

1.3 User Management API
    ├── GET /api/users/me
    ├── PATCH /api/users/me
    ├── GET /api/users/me/credits
    └── GET /api/users/me/history
```

### Deliverables
- [ ] Supabase project setup
- [ ] Database migrations
- [ ] Auth middleware (Python + Next.js)
- [ ] User CRUD endpoints

### Interface Contract
```typescript
// Other workstreams can depend on:
type User = {
  id: string;
  email: string;
  credits: number;
}

// Auth middleware provides:
function getCurrentUser(request): User | null
function requireAuth(request): User  // throws if not authenticated
function requireCredits(request, amount: number): void  // throws if insufficient
```

---

## WORKSTREAM 2: Credits & Payments
**Agent Focus**: Stripe integration, credit system, billing

### Tasks
```
2.1 Stripe Integration
    ├── Product/Price setup (10, 30, 100, 500 credit packs)
    ├── Checkout session creation
    ├── Webhook handling (payment success/failure)
    └── Customer portal for invoices

2.2 Credit System
    ├── Credit balance tracking
    ├── Credit deduction (atomic transactions)
    ├── Credit history/audit log
    └── Low balance notifications

2.3 Billing API
    ├── POST /api/billing/checkout (create Stripe session)
    ├── POST /api/billing/webhook (Stripe webhooks)
    ├── GET /api/billing/history
    └── GET /api/billing/portal (Stripe customer portal)
```

### Deliverables
- [ ] Stripe account setup + products
- [ ] Checkout flow
- [ ] Webhook handlers
- [ ] Credit transaction system

### Interface Contract
```python
# Other workstreams can use:
async def deduct_credits(user_id: str, amount: int, reason: str) -> bool
async def get_credit_balance(user_id: str) -> int
async def add_credits(user_id: str, amount: int, transaction_id: str) -> None

# Credit costs (config):
CREDIT_COSTS = {
    "character_generation": 1,
    "animation_generation": 1,
}
```

---

## WORKSTREAM 3: Generation Engine
**Agent Focus**: Core AI generation logic, job queue, fal.ai integration

### Tasks
```
3.1 Job Queue System
    ├── Redis/BullMQ queue setup
    ├── Job status tracking (pending, processing, completed, failed)
    ├── Progress updates (SSE or WebSocket)
    └── Retry logic with exponential backoff

3.2 Generation Workers
    ├── Character generation worker
    ├── Animation generation worker
    ├── Video processing worker (ping-pong)
    ├── GIF conversion worker
    └── Green screen processing worker

3.3 Generation API
    ├── POST /api/generate/character
    ├── POST /api/generate/animations
    ├── GET /api/generate/status/:jobId
    └── GET /api/generate/stream/:jobId (SSE progress)
```

### Deliverables
- [ ] Queue infrastructure (Redis)
- [ ] Worker processes
- [ ] Progress streaming
- [ ] Error handling + retries

### Interface Contract
```python
# Job creation:
async def create_character_job(
    user_id: str,
    prompt: str,
    style: str
) -> Job

async def create_animation_job(
    user_id: str,
    character_id: str,
    states: list[str]
) -> Job

# Job status:
class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Job:
    id: str
    status: JobStatus
    progress: int  # 0-100
    result: dict | None
    error: str | None
```

---

## WORKSTREAM 4: Asset Storage
**Agent Focus**: File storage, CDN, asset management

### Tasks
```
4.1 Storage Setup
    ├── S3/Cloudflare R2 bucket configuration
    ├── Signed URL generation (upload + download)
    ├── CDN configuration for fast delivery
    └── Automatic cleanup of old/orphaned files

4.2 Asset Management
    ├── Image optimization (thumbnails, webp)
    ├── Video transcoding if needed
    ├── GIF optimization
    └── ZIP download for bulk export

4.3 Storage API
    ├── POST /api/assets/upload-url (get signed upload URL)
    ├── GET /api/assets/:id
    ├── DELETE /api/assets/:id
    └── POST /api/assets/download-all/:characterId (ZIP)
```

### Deliverables
- [ ] S3/R2 bucket setup
- [ ] Upload/download signed URLs
- [ ] CDN configuration
- [ ] Asset cleanup cron job

### Interface Contract
```python
# Other workstreams can use:
async def upload_file(file_bytes: bytes, filename: str, content_type: str) -> str  # returns URL
async def get_signed_url(asset_id: str, expires_in: int = 3600) -> str
async def delete_asset(asset_id: str) -> None
async def create_zip_download(asset_ids: list[str]) -> str  # returns download URL
```

---

## WORKSTREAM 5: Frontend - Core UI
**Agent Focus**: Next.js setup, layouts, shared components

### Tasks
```
5.1 Project Setup
    ├── Next.js 14 + TypeScript
    ├── Tailwind CSS + Shadcn/UI
    ├── Authentication pages (login, register, forgot password)
    └── Protected route middleware

5.2 Layout & Navigation
    ├── Dashboard layout (sidebar, header)
    ├── Mobile responsive navigation
    ├── User dropdown (profile, billing, logout)
    └── Credit balance display

5.3 Shared Components
    ├── Loading states / skeletons
    ├── Error boundaries
    ├── Toast notifications
    ├── Modal system
    └── Form components
```

### Deliverables
- [ ] Next.js project with auth
- [ ] Dashboard layout
- [ ] Component library
- [ ] API client setup (React Query)

### File Structure
```
frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   └── register/
│   ├── (dashboard)/
│   │   ├── layout.tsx
│   │   ├── page.tsx (home/gallery)
│   │   ├── create/
│   │   ├── character/[id]/
│   │   └── billing/
│   └── api/
├── components/
│   ├── ui/ (shadcn)
│   ├── layout/
│   └── shared/
├── lib/
│   ├── api.ts
│   ├── auth.ts
│   └── utils.ts
└── hooks/
```

---

## WORKSTREAM 6: Frontend - Creator Studio
**Agent Focus**: Character creation UI, animation generation, preview

### Tasks
```
6.1 Character Creator
    ├── Prompt input with suggestions
    ├── Style selector (visual cards)
    ├── Advanced options (expandable)
    └── Generate button with loading state

6.2 Preview & Approval
    ├── Character preview display
    ├── Approve / Regenerate buttons
    ├── Version history sidebar
    └── Comparison view (before/after)

6.3 Animation Generator
    ├── Animation state selector (multi-select)
    ├── Generation progress display
    ├── Real-time status updates (SSE)
    └── Preview generated animations

6.4 Results & Download
    ├── Animation gallery grid
    ├── Video/GIF preview players
    ├── Individual download buttons
    ├── Download all (ZIP) button
    └── Share/embed options
```

### Deliverables
- [ ] Character creation page
- [ ] Animation generation page
- [ ] Progress/status components
- [ ] Download functionality

### Key Components
```typescript
// Components to build:
<CharacterPromptInput />
<StyleSelector styles={STYLES} onSelect={...} />
<AnimationStateSelector states={STATES} onSelect={...} />
<GenerationProgress jobId={...} />
<CharacterPreview character={...} onApprove={...} onRegenerate={...} />
<AnimationGallery animations={...} />
<VideoPlayer src={...} loop autoPlay />
<DownloadButton asset={...} format="gif" | "mp4" | "zip" />
```

---

## WORKSTREAM 7: Frontend - Gallery & History
**Agent Focus**: Asset gallery, character management, history

### Tasks
```
7.1 Gallery View
    ├── Grid of all characters
    ├── Filter by date, style
    ├── Search by prompt
    └── Pagination / infinite scroll

7.2 Character Detail Page
    ├── Character info display
    ├── All animations for character
    ├── Regenerate animations option
    ├── Delete character option
    └── Download all assets

7.3 History & Usage
    ├── Generation history list
    ├── Credit usage breakdown
    ├── Cost per generation
    └── Export history (CSV)
```

### Deliverables
- [ ] Gallery page
- [ ] Character detail page
- [ ] History page
- [ ] Search & filter functionality

---

## WORKSTREAM 8: Frontend - Billing UI
**Agent Focus**: Pricing page, checkout, billing portal

### Tasks
```
8.1 Pricing Display
    ├── Credit pack cards
    ├── Feature comparison
    ├── Current balance display
    └── "Most popular" badge

8.2 Checkout Flow
    ├── Pack selection
    ├── Stripe Checkout redirect
    ├── Success/cancel pages
    └── Credit balance update

8.3 Billing Portal
    ├── Purchase history
    ├── Invoice downloads
    ├── Stripe portal link
    └── Credit usage charts
```

### Deliverables
- [ ] Pricing page
- [ ] Checkout integration
- [ ] Billing history page
- [ ] Usage dashboard

---

## WORKSTREAM 9: Infrastructure & DevOps
**Agent Focus**: Deployment, CI/CD, monitoring

### Tasks
```
9.1 Deployment Setup
    ├── Vercel (frontend)
    ├── Railway/Fly.io (backend + workers)
    ├── Environment configuration
    └── Domain + SSL setup

9.2 CI/CD Pipeline
    ├── GitHub Actions workflows
    ├── Automated testing
    ├── Preview deployments
    └── Production deployment

9.3 Monitoring & Logging
    ├── Error tracking (Sentry)
    ├── API monitoring
    ├── Queue monitoring
    └── Cost tracking dashboard
```

### Deliverables
- [ ] Production deployment
- [ ] CI/CD pipelines
- [ ] Monitoring setup
- [ ] Documentation

---

## Execution Order

### Phase 1: Foundation (Parallel)
Run these workstreams simultaneously:
```
Agent A: WORKSTREAM 1 (Database & Auth)
Agent B: WORKSTREAM 2 (Credits & Payments)
Agent C: WORKSTREAM 4 (Asset Storage)
Agent D: WORKSTREAM 5 (Frontend Core UI)
```

### Phase 2: Core Features (Parallel)
After Phase 1 interfaces are ready:
```
Agent A: WORKSTREAM 3 (Generation Engine)
Agent B: WORKSTREAM 6 (Creator Studio UI)
```

### Phase 3: Polish (Parallel)
```
Agent A: WORKSTREAM 7 (Gallery & History)
Agent B: WORKSTREAM 8 (Billing UI)
Agent C: WORKSTREAM 9 (Infrastructure)
```

---

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind, Shadcn/UI |
| Backend | FastAPI (Python) |
| Database | DigitalOcean Managed Postgres |
| Auth | Custom JWT or Supabase Auth |
| Queue | DigitalOcean Managed Redis + Celery |
| Storage | DigitalOcean Spaces (S3-compatible) |
| CDN | DigitalOcean Spaces CDN |
| Payments | Stripe |
| Hosting | DigitalOcean App Platform |
| Monitoring | Sentry, DigitalOcean Monitoring |

---

## DigitalOcean Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DigitalOcean App Platform                     │
│  ┌─────────────────────┐    ┌─────────────────────┐             │
│  │  Frontend Service   │    │  Backend Service    │             │
│  │  (Next.js SSR)      │    │  (FastAPI)          │             │
│  │  $12/mo basic       │    │  $12/mo basic       │             │
│  └─────────────────────┘    └─────────────────────┘             │
│                                      │                           │
│  ┌─────────────────────┐    ┌───────┴───────┐                   │
│  │  Worker Service     │    │  Worker       │                   │
│  │  (Celery)           │    │  (Celery)     │                   │
│  │  $12/mo basic       │    │  Scale as     │                   │
│  │                     │    │  needed       │                   │
│  └─────────────────────┘    └───────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Managed Services                              │
│  ┌─────────────────────┐    ┌─────────────────────┐             │
│  │  Managed Postgres   │    │  Managed Redis      │             │
│  │  $15/mo (1GB)       │    │  $15/mo (1GB)       │             │
│  │  Auto backups       │    │  For job queue      │             │
│  └─────────────────────┘    └─────────────────────┘             │
│                                                                  │
│  ┌─────────────────────────────────────────────┐                │
│  │  Spaces (S3-compatible storage)             │                │
│  │  $5/mo (250GB) + $0.02/GB transfer          │                │
│  │  Built-in CDN for fast asset delivery       │                │
│  └─────────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

### DigitalOcean Monthly Costs (Estimated)

| Service | Starter | Growth | Scale |
|---------|---------|--------|-------|
| App Platform (FE) | $12 | $24 | $48 |
| App Platform (BE) | $12 | $24 | $48 |
| App Platform (Workers) | $12 | $36 | $96 |
| Managed Postgres | $15 | $30 | $60 |
| Managed Redis | $15 | $15 | $30 |
| Spaces (Storage) | $5 | $10 | $20 |
| **Total Infra** | **$71/mo** | **$139/mo** | **$302/mo** |

### App Platform Configuration

```yaml
# .do/app.yaml
name: animation-creator
services:
  - name: frontend
    github:
      repo: your-org/animation-creator
      branch: main
      deploy_on_push: true
    source_dir: frontend
    build_command: npm run build
    run_command: npm start
    http_port: 3000
    instance_size_slug: basic-xxs
    instance_count: 1
    routes:
      - path: /

  - name: backend
    github:
      repo: your-org/animation-creator
      branch: main
      deploy_on_push: true
    source_dir: backend
    dockerfile_path: backend/Dockerfile
    http_port: 8000
    instance_size_slug: basic-xxs
    instance_count: 1
    routes:
      - path: /api

workers:
  - name: celery-worker
    github:
      repo: your-org/animation-creator
      branch: main
    source_dir: backend
    dockerfile_path: backend/Dockerfile.worker
    instance_size_slug: basic-xxs
    instance_count: 1

databases:
  - name: db
    engine: PG
    production: true
    cluster_name: animation-creator-db

  - name: redis
    engine: REDIS
    production: true
    cluster_name: animation-creator-redis
```

---

## Cash Flow & fal.ai Strategy

### The Cash Flow Advantage

```
Timeline:
Day 1:  User buys 10 credits ($19.99)      → You receive $19.99
Day 2:  User generates character            → fal.ai charges ~$0.05
Day 3:  User generates 4 animations         → fal.ai charges ~$1.00
Day 30: fal.ai bills you                    → You pay ~$1.05

Result: You held $19.99 for 30 days before paying $1.05
        Net: +$18.94 in your account
```

**This is POSITIVE cash flow** - you get paid before you pay.

### Recommended Strategy

#### Option 1: Cash Buffer (Recommended for Start)
```
Keep 2 months of expected API costs as buffer:

Expected users: 100
Expected API cost/mo: ~$400
Buffer needed: $800

As you grow, increase buffer proportionally.
```

#### Option 2: fal.ai Prepaid Credits
```
fal.ai offers prepaid credits at discount:
- Check their pricing page for volume discounts
- Prepay when you have predictable usage
- Good for reducing per-generation cost
```

#### Option 3: Revenue-Based Buffer
```
Rule: Always keep 20% of revenue as API buffer

Revenue this month: $4,000
Set aside for API: $800
Available for you: $3,200
Actual API cost: ~$400
Remaining buffer: $400 (rolls over)
```

### Cash Flow Projection

| Month | Users | Revenue | API Cost | Net | Cumulative |
|-------|-------|---------|----------|-----|------------|
| 1 | 50 | $1,000 | $200 | $800 | $800 |
| 2 | 100 | $2,000 | $400 | $1,600 | $2,400 |
| 3 | 200 | $4,000 | $800 | $3,200 | $5,600 |
| 4 | 350 | $7,000 | $1,400 | $5,600 | $11,200 |
| 5 | 500 | $10,000 | $2,000 | $8,000 | $19,200 |
| 6 | 700 | $14,000 | $2,800 | $11,200 | $30,400 |

### Risk Mitigation

```
1. Credit Limits
   - New users: Max 50 credits/day
   - Prevents abuse/runaway costs

2. Pre-validation
   - Verify payment before allowing generation
   - No "free trials" that cost you API money

3. Failed Generation Policy
   - If fal.ai fails, refund credits
   - You still pay API cost, but it's rare (~1%)
   - Build this into your margin (already 90%)

4. Rate Limiting
   - Prevent rapid-fire generation
   - 1 generation at a time per user
   - Queue system handles this naturally
```

### Payment Timing Optimization

```
Stripe payouts:        Weekly (every Friday)
fal.ai billing:        Monthly (end of month)

Week 1-4: Collect revenue
End of month: Pay fal.ai bill from collected revenue

You always have cash before you need to pay.
```

---

## API Endpoints Summary

```
Authentication:
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/me

Users:
GET    /api/users/me
PATCH  /api/users/me
GET    /api/users/me/credits

Billing:
POST   /api/billing/checkout
POST   /api/billing/webhook
GET    /api/billing/history
GET    /api/billing/portal

Generation:
POST   /api/generate/character
POST   /api/generate/animations
GET    /api/generate/status/:jobId
GET    /api/generate/stream/:jobId

Characters:
GET    /api/characters
GET    /api/characters/:id
DELETE /api/characters/:id

Animations:
GET    /api/animations/:characterId
DELETE /api/animations/:id

Assets:
GET    /api/assets/:id
POST   /api/assets/download-zip
```

---

## File Structure

```
animation-creator-saas/
├── frontend/                 # Next.js app
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
├── backend/                  # FastAPI app
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── services/
│   │   └── workers/
│   ├── requirements.txt
│   └── main.py
├── shared/                   # Shared types/contracts
│   └── types.ts
├── infrastructure/
│   ├── docker-compose.yml
│   └── terraform/
└── docs/
    ├── API.md
    └── DEPLOYMENT.md
```

---

## Getting Started

To begin development, each agent should:

1. Read their assigned workstream
2. Review the interface contracts they must implement
3. Review the interface contracts they depend on
4. Start with the deliverables checklist
5. Create PR with tests for their workstream

Agents can work in parallel as long as they respect the interface contracts.
