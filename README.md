<img src="screenshots/logo-mark.svg" width="56" alt="StartLine mark: a running track with a start line">

# StartLine: find your next start line

> **Submitted by:** Pratyush Mohanty  |  **Roll No.:** 24BCS10238

**DevOps Final Capstone (Session 21)** · [Grading rubric, item by item](#21-grading-rubric-where-each-item-is) · Verified run log: [output.md](output.md) · Screenshots: [screenshots/](screenshots/)

StartLine is a sports-events platform for amateur athletes in India's Tier 1 and
Tier 2 cities. You pick one or more sports and answer two or three quick
questions per sport. You then see **215 real upcoming events** (marathons,
brevets, sea swims, triathlons, HYROX, Devils Circuit, and badminton, tennis,
pickleball, squash, table tennis and football tournaments) ranked by how well
they fit you. Each event has an **event guide** with a race-day timeline
anchored to the real start time and the city's climate for that month. A
**readiness calculator** estimates your finish time and gives a week-by-week
runway. You can **register** and get a race bib, then plan your **season**
with recovery warnings between races.

The point of the capstone is not the app on its own. It is how a commit travels
from a laptop to a monitored, autoscaling Kubernetes deployment: tests, Docker
images, a Trivy security gate, GHCR, Terraform for AWS VPC + EKS, Helm,
Ingress, HPA, Prometheus and Grafana, and a troubleshooting lab where things
are broken on purpose.

### Project Walkthrough Video

[https://drive.google.com/file/d/1hU0ZT3mtIxDQSZTKGAL_wMOYjKHqnQrf/view?usp=sharing](url)

![Discover page with personalised picks](screenshots/app-discover-picks.jpg)

| | |
|---|---|
| ![Profile questions](screenshots/app-profile-questions.jpg) Two or three questions per sport | ![IRONMAN 70.3 for a beginner](screenshots/app-event-ironman-match.jpg) An honest "Stretch" for a beginner triathlete |
| ![Readiness](screenshots/app-readiness-triathlon.jpg) Readiness with split estimates | ![Event guide](screenshots/app-event-guide.jpg) Event guide: weather, timeline, kit |
| ![Bib](screenshots/app-register-bib.jpg) Registration ends with a race bib | ![Season](screenshots/app-season.jpg) Season plan with recovery warnings |
| ![Mobile](screenshots/app-mobile.jpg) Mobile | ![Grafana during the rush](screenshots/grafana-dashboard-rush.jpg) Grafana during the HPA demo |

---

## Contents

1. [What the app does](#1-what-the-app-does)
2. [Architecture](#2-architecture)
3. [Repository structure](#3-repository-structure)
4. [The data: real events, researched](#4-the-data-real-events-researched)
5. [Run it locally](#5-run-it-locally)
6. [API](#6-api)
7. [Testing: the first quality gate](#7-testing-the-first-quality-gate)
8. [Docker](#8-docker)
9. [CI/CD with GitHub Actions](#9-cicd-with-github-actions)
10. [Security scanning](#10-security-scanning)
11. [Terraform: AWS VPC + EKS](#11-terraform-aws-vpc--eks)
12. [Kubernetes and Helm](#12-kubernetes-and-helm)
13. [Ingress](#13-ingress)
14. [HPA: autoscaling under a registration rush](#14-hpa-autoscaling-under-a-registration-rush)
15. [Monitoring: Prometheus and Grafana](#15-monitoring-prometheus-and-grafana)
16. [Troubleshooting lab](#16-troubleshooting-lab)
17. [PostgreSQL in Kubernetes vs Amazon RDS](#17-postgresql-in-kubernetes-vs-amazon-rds)
18. [Final demo, step by step](#18-final-demo-step-by-step)
19. [Interface design](#19-interface-design)
20. [Honest limitations](#20-honest-limitations)
21. [Grading rubric: where each item is](#21-grading-rubric-where-each-item-is)

---

## 1. What the app does

| Feature | How it works |
|---|---|
| **Sports and cities** | 13 sports, 36 hub cities (8 Tier 1, 28 Tier 2). Events in 29 of them. Filter by sport (multi-select chips with live counts), city, radius (50 / 150 / 400 km, haversine distance), month, level, "registration open", "beginner friendly", free-text search. "Near me" maps browser geolocation to the closest hub city. |
| **Profile: 2-3 questions per sport** | Sport-specific and required. Swimming asks your level, how far you can swim non-stop and your open-water experience. Triathlon asks your level, longest multisport race and weakest leg. Pickleball asks your DUPR band, format and age group. Every answer has a concrete hint ("400 m-1 km: about 15-30 minutes of steady swimming"). No password; the browser remembers only the profile id. |
| **Recommendation engine** | Scores every category of every event for fit (level, distance you can handle, format, age and rating brackets, open-water or trail experience), then mixes in distance from your city, weeks left to prepare and whether entries are open. Matches appear first under **Picked for you**, each with its reasons ("1 km is within your non-stop swim (400 m-1 km)", "The natural next step: sprint") and cautions ("2 km swim: your weakest leg"). **One switch turns recommendations off** for a plain date-sorted list. Details: [backend/app/engine/README.md](backend/app/engine/README.md). |
| **Readiness calculator** | Per category: Riegel prediction for runs (ITRA effort distance on trails), speed and stop time against ACP brevet limits for rides, open-water-adjusted pace for swims, split-by-split triathlon estimate with IRONMAN cutoffs, HYROX and OCR models, and tournament-day load for racquet and team sports. The result is a 0-100 score on a running-track gauge, a verdict, the weighted components, gaps to close and a week-by-week runway to race day. |
| **Event guide** | Race-day timeline with clock times from the real start ("T-90 min" becomes "03:30"), heat index at the start from IMD climate normals with NWS bands, CPCB air-quality note in winter, interactive kit checklist, fuel and hydration, safety, first-timer tips, glossary, organiser tips, venue map link. |
| **Registration** | Category cards with fee, start and cutoff. Server-side checks: entries closed, minimum age on race day, age-group and rating brackets, doubles need a partner, relays and teams need a team name, Indian mobile format, a different emergency contact, no duplicate entry. You get a race bib (number + code) and a calendar file. |
| **My season** | Registered and saved events by month with countdowns, latest readiness score and **recovery warnings** ("Only 7 days between Tata Mumbai Marathon and Telangana Half Marathon. Recovery after Half Marathon usually takes about 13 days."). Your bibs, with cancel. |
| **Extras** | Save events, add to calendar (`.ics`), related events nearby, sport pages explaining formats and what suits each level, mobile layout with a bottom tab bar. |

## 2. Architecture

```mermaid
flowchart LR
  dev([Developer]) -->|git push| gh[(GitHub)]
  gh --> ci
  subgraph ci[GitHub Actions - ci-cd.yml]
    direction TB
    t[pytest + ruff<br/>Alembic up/down on Postgres<br/>React build] --> b[docker build<br/>tag = commit SHA]
    b --> s[Trivy scan<br/>HIGH/CRITICAL with a fix = fail]
    s --> p[push to GHCR]
    p --> d[helm upgrade --install<br/>on EKS via OIDC]
  end
  tf[Terraform] -->|VPC, subnets, NAT, IAM, EKS, add-ons| aws[(AWS ap-south-1)]
  d --> k8s
  subgraph k8s[Kubernetes namespace startline]
    ing[Ingress<br/>startline.local] -->|/api /docs| be[FastAPI x2-6<br/>HPA on CPU]
    ing -->|/| fe[React on nginx x2]
    be --> db[(PostgreSQL 17<br/>StatefulSet + PVC)]
  end
  prom[Prometheus] -->|ServiceMonitor /metrics| be
  graf[Grafana] --> prom
```

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 8, React Router 8, hand-written CSS (no UI kit), self-hosted Barlow Condensed + Inter, custom sport icon set |
| Backend | Python 3.13, FastAPI, SQLAlchemy 2.1, Alembic, Pydantic 2, prometheus-fastapi-instrumentator |
| Database | PostgreSQL 17 (StatefulSet + PVC in Kubernetes) |
| Tests | pytest (52 tests, 84% coverage), ruff |
| Containers | Multi-stage Docker images, non-root, Docker Compose for the full local stack |
| CI/CD | GitHub Actions, Trivy 0.74.0, GitHub Container Registry |
| Infrastructure | Terraform (AWS provider 6), VPC + EKS in ap-south-1, verified on LocalStack |
| Platform | Kubernetes 1.37 (kind), Helm 4, ingress-nginx, metrics-server, kube-prometheus-stack |

## 3. Repository structure

```text
startline/
├── frontend/                 React app, CSS design system, Dockerfile, nginx template
├── backend/
│   ├── app/                  FastAPI app: models, routers, serializers, observability
│   │   ├── engine/           profiling, recommendations, readiness, guide, season (+ README)
│   │   └── seed/             seed loader + data/ (cities, sports, events/<sport>.json)
│   ├── alembic/              database migrations
│   ├── tests/                pytest suite (API, engine, registrations, seed)
│   └── Dockerfile, entrypoint.sh
├── research/                 raw research JSON (with source URLs) + build_seed.py
├── docker-compose.yml        full local stack
├── terraform/                AWS VPC + EKS + GitHub deploy role (run.sh: LocalStack, aws.sh: real AWS)
├── helm/startline/           Kubernetes package (values, values-dev, values-prod)
├── k8s/                      namespace (restricted Pod Security Standard), gp3 StorageClass for EKS
├── monitoring/               kube-prometheus-stack values, Grafana dashboard, install.sh
├── troubleshooting/          deliberately broken manifests + run.sh
├── scripts/                  deploy.sh (deploy a commit's GHCR images), registration-rush load test
├── security/reports/         Trivy reports
├── .github/workflows/        ci-cd.yml
├── output.md                 verbatim output of every step
└── screenshots/
```

## 4. The data: real events, researched

The catalogue is real. Five research passes covered road running (Tier 1, then
Tier 2 and trail), triathlon and swimming, cycling, HYROX and OCR, and racquet
and team sports. They collected events from organiser websites, federation
calendars (AITA, BAI, TTFI, SRFI, Audax India, ITF) and registration
platforms. Two more passes wrote the sport content: profile questions,
readiness constants with sources, kit lists, timelines, safety and glossaries.
A last pass collected IMD climate normals and CPCB air-quality notes for all
36 cities.

| | |
|---|---|
| Events | **215** (140 dates confirmed, 75 "expected"), 812 categories, 17 Oct 2026 to 10 Oct 2027 |
| Source URLs | 458, shown on every event page |
| Cities with events | 29: Bengaluru 29, Mumbai 21, Pune 19, Hyderabad 18, Delhi NCR 18, Chennai 17, Goa 13, Kolkata 12, Ahmedabad 11, Mangaluru 7, Kochi 6, Mysuru 6, and 17 more Tier 2 cities |
| Guide content | 162 kit items, 111 timeline steps, 144 glossary terms across 13 sports |

| Sport | Events | Profile questions |
|---|---:|---|
| Road running | 76 | Level · Longest recent run · 5K time |
| Trail & ultra | 16 | Level · Longest trail race · Biggest climb |
| Cycling | 18 | Level · Longest ride · Solo speed |
| Swimming | 15 | Level · Non-stop swim · Open water |
| Triathlon | 21 | Level · Race history · Weakest leg |
| Fitness racing (HYROX) | 9 | Level · Division · 5K time |
| Obstacle racing | 9 | Level · Running · Grip |
| Badminton | 11 | Level · Format · Age group |
| Tennis | 13 | Rating · Format · Age group |
| Pickleball | 9 | DUPR · Format · Age group |
| Table tennis | 4 | Level · Format · Age group |
| Squash | 7 | Level · Age group · Tournaments |
| Football | 7 | Level · Format · Team |

Rules the research followed: an event needs a source that was actually opened;
unknown numbers stay empty rather than guessed. When a 2026-27 date is not
published yet, the event uses its usual weekend from previous editions. It is
marked **Expected date** everywhere, with the last edition's date shown. Basketball
was dropped because only one recurring public event could be verified.

`research/build_seed.py` turns the raw files into `backend/app/seed/data/`. On
every start the backend runs `python -m app.seed`, an idempotent upsert keyed on
slugs that never touches registrations. It runs behind a Postgres advisory lock
so several replicas can start at once.

## 5. Run it locally

**Docker Compose (whole stack):**

```bash
docker compose up --build
```

| URL | |
|---|---|
| http://localhost:3000 | the app (nginx serves React and proxies `/api`) |
| http://localhost:8000/docs | FastAPI Swagger |
| http://localhost:8000/health, /ready, /metrics | probes and Prometheus metrics |

`docker compose down` stops it; `docker compose down -v` also deletes the
database volume. Postgres is published on `127.0.0.1:5433` for inspection.

![docker compose up --build](screenshots/docker-compose-up-build.png)

![docker compose ps](screenshots/docker-compose-ps.png)

**Backend directly** (Python 3.12+, a Postgres):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL='postgresql+psycopg://startline:startline-local@localhost:5433/startline'
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

**Frontend directly:** `cd frontend && npm ci && npm run dev` (http://localhost:5173, `/api` proxied to :8000).

## 6. API

Swagger is at `/docs`.

| Method | Path | |
|---|---|---|
| GET | `/`, `/health`, `/ready`, `/metrics` | service info, liveness, readiness (DB + seeded catalogue), Prometheus |
| GET | `/api/stats` | catalogue and usage counts |
| GET | `/api/cities`, `/api/sports`, `/api/sports/{slug}` | catalogue, sport pages with questions, guide, rules |
| GET | `/api/events` | discovery: `sport`, `city`, `radius_km`, `month`, `level`, `registration`, `beginner_friendly`, `q`, `sort`, `athlete_id`, `recommend` |
| GET | `/api/events/{slug}` | detail, match, weather, related events |
| GET | `/api/events/{slug}/guide` | event guide for a category |
| GET | `/api/events/{slug}/readiness-form` | calculator fields, prefilled from the profile |
| GET | `/api/events/{slug}/calendar.ics` | calendar file |
| POST/GET/PUT/PATCH/DELETE | `/api/athletes[/{id}]` | profile with answers; PATCH toggles recommendations |
| POST/DELETE | `/api/athletes/{id}/saved[/{slug}]` | save events |
| GET | `/api/athletes/{id}/season`, `/registrations` | season plan with recovery warnings |
| POST | `/api/readiness` | readiness calculator |
| POST/GET/DELETE | `/api/registrations[/{code}]` | register, look up, cancel |

## 7. Testing: the first quality gate

```bash
cd backend && pytest -q
```

There are 52 tests (84% line coverage), run against SQLite seeded with the real catalogue, with "today"
pinned to 15 Oct 2026 so the dates give the same answers on every run:

* **API**: probes, catalogue rules (every sport has 2-3 questions; only Tier 1 and 2 cities), profile validation, recommendations first and sorted by score, recommendations off gives date order, filters, guide timeline anchored to the start, calendar export.
* **Engine**: age, rating and format parsing, rated-draw eligibility, kids categories never picked for adults, first-triathlon wording, the Riegel formula (5K 25:00 to 10K 52:07), brevet ACP limit, triathlon splits adding up, heat index against the NWS chart.
* **Registrations**: bib numbers, duplicates (409), minimum age on race day, phone and declaration checks, doubles partner, cancel, recovery warnings.
* **Seed**: every event sourced and upcoming, no em dashes, upsert idempotent.

The tests already caught a real bug before any image was built.
`"Mixed Doubles 3.5 and Doubles 3.5"` was parsed as mixed-only, so doubles
players were never matched to it.

```text
Bad code -> pytest fails -> pipeline stops -> no image is built, scanned or pushed
```

![pytest -v](screenshots/pytest-v.png)

## 8. Docker

| Image | Base | Size | Notes |
|---|---|---:|---|
| `startline-backend` | python:3.13-alpine, 2 stages | 183 MB | dependencies installed into a venv stage, pip removed, user 10001, HEALTHCHECK on /health, entrypoint runs migrations, then seed, then Uvicorn. Alpine replaced Debian slim to pass the strict Trivy gate (section 10) |
| `startline-frontend` | node:22-alpine build, nginx-unprivileged runtime | 114 MB | no Node in the runtime image, `apk upgrade` for late Alpine fixes, `BACKEND_URL` rendered at start |

```bash
docker build -t startline-backend:local ./backend
docker build -t startline-frontend:local ./frontend
```

## 9. CI/CD with GitHub Actions

[.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml):

```text
test ──> build-scan-push (backend, frontend in parallel) ──> deploy
```

| Job | Steps |
|---|---|
| **test** | checkout · Python 3.13 · ruff check + format · seed catalogue check · pytest with coverage + JUnit report · Alembic upgrade / check / downgrade / upgrade and seed on a real Postgres 17 service · Node 22 · `npm ci` + `npm run build` |
| **build-scan-push** | docker build tagged with the short commit SHA · install Trivy 0.74.0 (sha256 pinned in the workflow) · scan, fail on any HIGH/CRITICAL · upload report · on `main`: log in to GHCR with `GITHUB_TOKEN` and push |
| **deploy** | on `main` only, when the `AWS_DEPLOY_ROLE_ARN` repository variable is set: OIDC to AWS (no stored keys; the role is in `terraform/github-oidc.tf`) · `aws eks update-kubeconfig` · [`scripts/deploy.sh eks <sha>`](scripts/deploy.sh): ingress-nginx, the DB Secret, then `helm upgrade --install --atomic` with `values-prod.yaml` and `image.tag=<sha>` |

The image tag is always the commit SHA, so production traces back to source:

```text
commit 301bd07 -> ghcr.io/bypratyush/startline-backend:301bd07 -> pod image on EKS
```

| Pipeline run (all four jobs green) | Images in GHCR, tagged by commit |
|---|---|
| ![GitHub Actions run](screenshots/ci-run.jpg) | ![GHCR versions](screenshots/ghcr-backend-versions.jpg) |

The `test` job was run locally with [act](https://github.com/nektos/act) on a
throwaway copy of the repository; the log is in [output.md](output.md#ci-test-job-run-locally-with-act).

**Commit to running pods.** The deploy job and a local run use the same script,
so the demo works with or without AWS:

```bash
git commit -am "Discover: new hero line" && git push      # pipeline: test -> build -> Trivy -> GHCR
./scripts/deploy.sh kind                                  # waits for ghcr.io/.../startline-*:<sha>, then helm upgrade
kubectl -n startline get deploy -o wide                   # both Deployments now run the new SHA
```

On AWS the pipeline does the last step itself. With `AWS_DEPLOY_ROLE_ARN` set, the
deploy job signed in through OIDC and rolled commit `301bd07` out to EKS: 3 backend
and 3 frontend pods, Postgres on an encrypted gp3 volume, and the Ingress on an AWS
load balancer.

![The deploy job on EKS](screenshots/ci-deploy-eks.jpg)

The next push (`7ebf977`) then went the whole way by itself: tests, images, Trivy,
GHCR, and a rolling update on EKS. New backend and frontend pods came up on the new
tag, the database pod was left alone, and Helm moved to revision 2.

| The deploy job for `7ebf977` | Helm and the Deployments on EKS afterwards |
|---|---|
| ![Rolling update by the pipeline](screenshots/ci-deploy-eks-update.jpg) | ![Helm revision 2, images 7ebf977](screenshots/aws-eks-deployment-update.png) |

## 10. Security scanning

**What Trivy scans, and what the result means.** In the `build-scan-push` job,
Trivy 0.74.0 scans each freshly built image (backend and frontend) before it can
be pushed: the operating-system packages and every Python package in the
backend's virtualenv, against its vulnerability database. Any HIGH or CRITICAL
finding fails the job, whether or not a fix exists. Both images report **0 HIGH
and 0 CRITICAL** ([security/reports/](security/reports/)). That means no known
serious CVE ships in the images; it says nothing about bugs in our own code,
which is what the tests and code review are for.

**A CVE it found.** The backend first ran on `python:3.13-slim` (Debian 13). The
strict gate failed it with 44 HIGH findings: 8 CVEs across 16 Debian base
packages, mostly `util-linux` libraries. One of them, **CVE-2026-76642**: when an
external mount helper fails, util-linux's `mount` still runs privileged
post-mount hooks. Debian listed all 44 as "affected" with no fixed version, so a
rebuild could not clear them. StartLine never calls `mount`, but a gate should
not rest on that argument, so the backend moved to `python:3.13-alpine`, which
does not ship these packages: 0 findings, and the image went from 311 MB to
183 MB ([before](security/reports/trivy-backend-debian-slim-before.txt),
[after](security/reports/trivy-backend.txt)).

A scanner is one control, not a guarantee. These are the layers and where
StartLine stands on each:

| Layer | What it catches | In this project |
|---|---|---|
| SAST | insecure code patterns | ruff lint in CI; Bandit is the next step |
| Dependency scanning | vulnerable libraries | Trivy reads the Python packages inside the image; all pinned in `requirements.txt` and `package-lock.json` |
| Secret scanning | credentials in Git | no secrets in the repo: the DB password comes from a Kubernetes Secret, AWS access via OIDC, GHCR via `GITHUB_TOKEN` |
| Container scanning | OS and library CVEs in images | Trivy gate in CI: any HIGH/CRITICAL fails the build |
| Runtime security | what a running container may do | non-root users, read-only root filesystems, all capabilities dropped, seccomp RuntimeDefault, namespace enforces the `restricted` Pod Security Standard |

The same gate inside the pipeline, on the images it is about to push:

| Backend (`301bd07`, alpine 3.24.2) | Frontend (`301bd07`) |
|---|---|
| ![Trivy step, backend](screenshots/ci-trivy-backend.jpg) | ![Trivy step, frontend](screenshots/ci-trivy-frontend.jpg) |

Local scans of the same images:

![Trivy backend](screenshots/trivy-backend.png)
![Trivy frontend](screenshots/trivy-frontend.png)

## 11. Terraform: AWS VPC + EKS

[terraform/](terraform/) describes the production infrastructure in `ap-south-1`:

```text
AWS ap-south-1
 ├── VPC 10.40.0.0/16 (DNS hostnames on)
 ├── public subnets  10.40.1.0/24 (1a), 10.40.2.0/24 (1b)   -> Internet gateway, load balancers
 ├── private subnets 10.40.11.0/24 (1a), 10.40.12.0/24 (1b) -> worker nodes, no public IPs
 ├── NAT gateway (one shared, or one per AZ)                 -> private egress
 ├── IAM: cluster role, node role, EBS CSI role (Pod Identity)
 ├── IAM: GitHub OIDC provider + deploy role (only this repo's production deploy job may assume it)
 └── EKS 1.35 (API auth mode, control-plane logs)
       ├── managed node group: c7i-flex.large x2 (2 vCPU, 4 GiB; min 2, max 4), IMDSv2-only launch template
       ├── add-ons: vpc-cni, coredns, kube-proxy, eks-pod-identity-agent, aws-ebs-csi-driver, metrics-server
       └── access entry: the deploy role is cluster admin (it installs ingress-nginx and the release)
```

**Without an account, on LocalStack 4.14.0:** [terraform/run.sh](terraform/run.sh)

1. `terraform plan -var enable_eks=true` plans the full design: **44 resources**, including the cluster, node group, 6 add-ons, NAT and the deploy role's access entry.
2. `terraform apply -var enable_eks=false` creates the **29** network and IAM resources (LocalStack Community has no EKS API).
3. The AWS CLI lists them: VPC, 4 subnets with correct AZs and public-IP settings, route tables, IAM roles.
4. `terraform destroy` removes all 29.

![terraform run on LocalStack: plan, apply, AWS CLI, destroy](screenshots/terraform-localstack-run.png)

**Against a real AWS account:** [terraform/aws.sh](terraform/aws.sh) keeps its state in its own
workspace and uses your normal AWS credentials.

```bash
./terraform/aws.sh plan            # VPC + EKS + deploy role, saved plan
./terraform/aws.sh apply           # apply it, point kubectl at the cluster, print the deploy role ARN
gh variable set AWS_DEPLOY_ROLE_ARN --body "<role arn>"   # the CI deploy job now runs
./scripts/deploy.sh eks            # or push a commit and let the pipeline deploy
./terraform/aws.sh down            # remove the load balancer and volumes Kubernetes made, then terraform destroy
```

`down` matters: the ingress controller's load balancer and the database volume
are created by Kubernetes, not Terraform. Left behind, they block the VPC delete
and keep billing.

**The real run** (AWS account in ap-south-1, 16 Oct 2026). `terraform plan` showed
the same 44 resources as on LocalStack, and the apply created them. The pipeline
then deployed StartLine onto the cluster (section 9), reachable over the internet
through the load balancer.

| | |
|---|---|
| ![terraform plan on AWS](screenshots/aws-terraform-plan.png) `terraform plan`: 44 to add | ![VPC subnets](screenshots/aws-console-vpc-subnets.jpg) `startline-vpc`: 2 public and 2 private subnets in ap-south-1a and 1b |
| ![EKS cluster](screenshots/aws-console-eks.jpg) EKS `startline-eks`, Kubernetes 1.35, Active | ![EKS nodes](screenshots/aws-console-eks-nodes.jpg) the managed node group: 2 nodes, one per zone |
| ![kubectl on EKS](screenshots/aws-eks-kubectl.png) nodes, pods, Services, Ingress, volume, Helm release | ![StartLine on the AWS load balancer](screenshots/aws-app-elb.png) the app on the load balancer's address |

Two things only the real account showed, both fixed in Terraform:

1. **Free plan instance types.** New AWS accounts on the Free plan cannot launch
   `t3.medium`. The node group sat in `CREATING` while the Auto Scaling group logged
   "The specified instance type is not eligible for Free Tier". The nodes now use
   `c7i-flex.large` (same 2 vCPU and 4 GiB, Free plan eligible), and the node group
   takes a name prefix so a replacement can start before the old one is deleted.
2. **GitHub's OIDC subject.** The deploy job was refused with "Not authorized to
   perform sts:AssumeRoleWithWebIdentity". This repository sends GitHub's newer
   immutable subject, `repo:bypratyush@68912154/startline@1420597870:environment:production`,
   which names the owner and repository by ID, so a re-created repository with the
   same name cannot take over the role. The trust policy now matches it.

**Teardown.** `./terraform/aws.sh down` deleted the namespace, the retained gp3
volume and the load balancer, then `terraform destroy` removed all 44 resources.
It stalled once: the VPC CNI had left an unattached network interface from a
terminated node, and EKS's own cluster security group was still in the VPC. I
deleted both by hand, and `aws.sh` now removes them (and EKS's log group) itself.
Afterwards the account had no cluster, NAT gateway, load balancer, volume,
instance, VPC or IAM role left.

![terraform destroy on AWS: 44 destroyed](screenshots/aws-terraform-destroy.png)

## 12. Kubernetes and Helm

```bash
kubectl apply -f k8s/namespace.yaml          # namespace with the restricted Pod Security Standard
helm upgrade --install startline ./helm/startline -n startline -f helm/startline/values-dev.yaml
```

The chart [helm/startline](helm/startline) renders:

| Object | Purpose |
|---|---|
| Deployment `startline-backend` + Service + PodDisruptionBudget | FastAPI. Rolling updates with zero unavailable. A startup probe covers migrations; liveness hits `/health` (cheap); readiness hits `/ready` (DB + catalogue). Config and Secret checksums roll the pods when either changes. |
| Deployment `startline-frontend` + Service | nginx serving the React build, read-only root filesystem with emptyDirs for nginx's writable paths |
| StatefulSet `startline-db` + headless Service + PVC | PostgreSQL 17 with a 1 Gi volume (10 Gi gp3 in prod) |
| ConfigMap, Secret | non-secret settings; DB password (prod uses `existingSecret`) |
| Ingress | `/api` and `/docs` to the backend, `/` to the frontend |
| HorizontalPodAutoscaler | backend 2-6 replicas at 60% CPU |
| ServiceMonitor, PrometheusRule | scraping and 5 alerts (rendered only where the Prometheus Operator CRDs exist) |

| Values file | Use |
|---|---|
| `values.yaml` | defaults (GHCR images, HPA on, ingress off) |
| `values-dev.yaml` | kind: local images, Ingress on `startline.local` and `startline.localhost`, monitoring on |
| `values-prod.yaml` | EKS: GHCR image tag set by CI, DB Secret generated inside the cluster by `deploy.sh` (never in Git), gp3 storage (`k8s/storageclass-gp3.yaml`), HPA 3-10 |

Concepts in practice: `helm upgrade` rolls a new revision, `helm history`
lists them, and `helm rollback startline <rev>` restores one (see output.md).

![kubectl get pods](screenshots/kubectl-get-pods.png)
![kubectl get svc](screenshots/kubectl-get-svc.png)
![helm list](screenshots/helm-list.png)
![helm history](screenshots/helm-history.png)

The registrations table in the cluster's PostgreSQL:

![registrations table](screenshots/postgres-registrations.png)

## 13. Ingress

An Ingress is only configuration: the **ingress-nginx controller** implements it.

```text
startline.local/            -> startline-frontend (React)
startline.local/api/...     -> startline-backend  (FastAPI)
startline.local/docs        -> startline-backend  (Swagger)
```

On kind the controller listens on the host's port 80. Add
`127.0.0.1 startline.local` to `/etc/hosts`, or use `http://startline.localhost`,
which browsers and curl resolve to 127.0.0.1 with no setup. Both hosts are in
`values-dev.yaml`.

![The app through the Ingress at startline.localhost](screenshots/app-via-ingress.jpg)
![Swagger through the Ingress](screenshots/swagger-via-ingress.jpg)

## 14. HPA: autoscaling under a registration rush

`./scripts/registration-rush.sh` simulates the minute a big race opens entries:
3 pods x 8 workers search events with recommendations on (the most CPU-heavy
endpoint) for 3 minutes. It prints the HPA every 15 s.

Measured on the kind cluster (backend requests 100m CPU, limit 500m, HPA target 60%):

| | First run | After the fixes below |
|---|---:|---:|
| Replicas | 2 -> 4 -> 6 -> 3 -> 2 | 2 -> 4 -> 6 (in 30 s) -> 2 |
| Event searches served (3 load pods, 3 min) | about 2,100 (693 per load pod) | **19,379** |
| Average latency under load | 2,064 ms | **222 ms** |
| Failed requests | 34 HTTP 500 (DB pool timeouts) | **0** |

```text
TIME      CPU (avg / target)          REPLICAS
06:25:07  221% / 60%                  2
06:25:22  291% / 60%                  4
06:25:37  352% / 60%                  6
06:27:53  399% / 60%                  6      <- load ends at about 06:28
06:28:24  12% / 60%                   6
...                                          <- 60 s scale-down stabilisation, then back to 2
```

![kubectl get hpa](screenshots/hpa.png)

The full logs of both runs are in [output.md](output.md#hpa).

The first run scaled correctly but found three real problems, each fixed and re-measured:

1. **Slow hot path.** `/api/events` reloaded 215 events and 812 categories
   through the ORM on every request. It now serves the catalogue from an
   in-process cache rebuilt every 60 s, with memoised category parsing:
   54 ms down to 17 ms per request.
2. **Readiness probes failing under load.** For two minutes the HPA logged
   "did not receive metrics for targeted pods (pods might be unready)".
   CPU-throttled pods missed the default 1 s probe timeout and dropped out of
   the Service. Probe timeouts are now 3 s, because a throttled pod is slow,
   not dead.
3. **HTTP 500s from connection-pool exhaustion.** Grafana showed 0.27% errors.
   The pod logs gave the cause: `QueuePool limit of size 5 overflow 5 reached,
   connection timed out, timeout 30.00`. FastAPI runs sync handlers on up to 40
   threads, and each request held its DB connection while it scored events.
   Now the connection goes back to the pool before scoring starts. The pool is
   5 + 10 per replica, so 6 replicas stay under Postgres' 100 connections. A
   saturated pool answers **503 with Retry-After** instead of 500 (there is a
   test for it).

The HPA needs CPU requests on the pods and a metrics provider. kind uses
metrics-server; on EKS it is a managed add-on in `eks.tf`.

## 15. Monitoring: Prometheus and Grafana

```bash
./monitoring/install.sh          # kube-prometheus-stack 92.1.0 + the StartLine dashboard
```

Both UIs sit behind the same ingress-nginx as the app, so they open on their own
addresses (`*.localhost` needs no `/etc/hosts` entry):

| URL | |
|---|---|
| http://grafana.localhost/d/startline/startline-api-autoscaling-and-athletes | the StartLine dashboard (anonymous viewer; admin login `admin` / `startline-grafana`) |
| http://prometheus.localhost/targets | scrape targets, `/alerts` for the rules |

`./monitoring/install.sh open` still port-forwards them to :9090 and :3001.

* **`/metrics`** on the backend is Prometheus text format, from the cluster's backend Service:

  ![curl /metrics](screenshots/curl-metrics.png)

* **ServiceMonitor** (from the chart) makes the Prometheus Operator scrape
  `/metrics` on every backend pod. Both pods show **UP** at
  `job="startline-backend"`.
* **Metrics**:
  * HTTP: `startline_http_requests_total` and `startline_http_request_duration_seconds` by handler, from the instrumentator.
  * Business: `startline_registrations_total{sport,city_tier}`, `startline_readiness_checks_total{sport,verdict}`, `startline_event_searches_total{recommendations}`, `startline_recommendation_seconds`, `startline_readiness_score`, `startline_db_up`.
* **Alerts** (PrometheusRule): StartLineBackendDown, StartLineDatabaseUnreachable, StartLineHighErrorRate (>5% 5xx), StartLineSlowEventSearch (p95 > 500 ms), StartLineAutoscalerMaxed.
* **Grafana dashboard** "StartLine - API, autoscaling and athletes" ([monitoring/startline-dashboard.json](monitoring/startline-dashboard.json)). It answers the questions the spec asks:
  * How many requests are arriving, and to which endpoint?
  * Which endpoint is slow (p50/p95)?
  * Are errors increasing?
  * Is CPU rising against the HPA target?
  * Is the HPA scaling (current, desired, max)?
  * What are athletes doing (registrations by sport, readiness verdicts, recommendations on or off)?

**Outage simulation** ([output.md](output.md#13-alert-firing-during-an-outage)):
`kubectl scale deployment startline-backend --replicas=0`. Fifteen seconds later
`StartLineBackendDown` is *pending*. After its 1-minute `for:` window it is
*firing*, and it clears once the replicas are back.

| Prometheus targets (ServiceMonitor) | Outage simulation: StartLineBackendDown firing |
|---|---|
| ![targets](screenshots/prometheus-targets.jpg) | ![alert](screenshots/prometheus-alert-firing.jpg) |

![Grafana](screenshots/grafana-dashboard-rush.jpg)

## 16. Troubleshooting lab

`./troubleshooting/run.sh` breaks the deployment three ways and works through
each one like an on-call engineer. The output is in output.md.

| Fault | Symptom | Investigation | Root cause | Fix |
|---|---|---|---|---|
| [broken-image.yaml](troubleshooting/broken-image.yaml) | `ErrImagePull` then `ImagePullBackOff` | `kubectl get pods`, `describe pod`, events | tag `v2.0-final` was never built | `kubectl set image` to a real tag (CI uses the commit SHA) |
| [broken-service.yaml](troubleshooting/broken-service.yaml) | requests to `startline-api` fail | `get svc`, `get endpointslices` (none), `get pods --show-labels` | selector `component=api`, pods are `component=backend` | patch the selector; endpoints appear |
| [broken-readiness.yaml](troubleshooting/broken-readiness.yaml) | pod `Running` but `READY 0/1` | `describe` (readiness 503), `/health` 200 vs `/ready` 503 from inside the pod | hard-coded wrong DB password | take `DB_PASSWORD` from the Secret |

The lesson in each: a Service selects pods by labels (no match means no
endpoints), and liveness and readiness answer different questions.

## 17. PostgreSQL in Kubernetes vs Amazon RDS

For the classroom and kind, Postgres runs as a StatefulSet with a PVC: one
command brings up everything, and it costs nothing. For production on AWS,
**Amazon RDS** (Multi-AZ) is the better default:

| | StatefulSet + EBS | Amazon RDS |
|---|---|---|
| Failover | manual: one replica, volume pinned to one AZ | automatic Multi-AZ standby |
| Backups and point-in-time restore | you build them (pg_dump CronJob to S3) | built in |
| Upgrades and patching | you | managed maintenance windows |
| Cost | cheapest | higher, but less operational risk |

Switching only changes `DB_HOST` and the Secret; the app already reads both
from configuration.

## 18. Final demo, step by step

| # | Show | How |
|---|---|---|
| 1 | Application | http://startline.localhost: build a profile (Swimming beginner + Triathlon), see **Picked for you** with reasons, flip recommendations off |
| 2 | API | http://startline.localhost/docs: `POST /api/athletes`, `GET /api/events?athlete_id=...`, `POST /api/registrations`, `DELETE /api/registrations/{code}` |
| 3 | Database | `kubectl -n startline exec -it startline-db-0 -- psql -U startline -c "select code, bib_number, full_name, status from registrations;"` |
| 4 | Git | change a visible line (for example the hero text), commit, push |
| 5 | CI | watch the run: `test` (ruff, 52 tests, Alembic on Postgres 17, React build), then `build-scan-push`, then `deploy` |
| 6 | Docker | the two images in the `build-scan-push` job, `docker image ls` locally |
| 7 | Security | Trivy step output: 0 HIGH/CRITICAL in both images |
| 8 | Registry and deploy | GHCR packages tagged with the new SHA; `./scripts/deploy.sh kind` (or the deploy job on EKS) rolls the pods to it, and the change shows in the browser |
| 9 | Terraform | walk through `vpc.tf`, `iam.tf`, `eks.tf`, `github-oidc.tf`, then `./terraform/run.sh` (or `aws.sh` on a real account) |
| 10 | Kubernetes | `kubectl get pods,svc -n startline` |
| 11 | Helm | `helm list -n startline`, `helm history startline -n startline` |
| 12 | Ingress | open the app and Swagger through `startline.local` |
| 13 | HPA | `./scripts/registration-rush.sh` and watch 2 -> 6 -> 2 |
| 14 | Monitoring | Prometheus targets and alerts, the Grafana dashboard during the rush |
| 15 | Failure | `./troubleshooting/run.sh service` (or `image`, `readiness`) |

## 19. Interface design

The aim: something an athlete would trust, made with care. Minimal, sharp and calm, sporty in the details rather than loud.

* **Logo.** A 400 m track seen from above, the lane surface in pitch green with a white lane line, and one ink start line painted across the home straight. It is instantly a track, it says "start line" without words, and it shares its geometry with the readiness gauge (a lap of the same track).
* **Colour.** Paper (`#f7f7f5`) and ink (`#0e1012`), with one primary: **pitch green** (`#126149`), the colour of every field, court and track infield, and of "go". Each sport keeps a muted identity colour, used only for its icon, a thin lane line on its list rows and faint line art behind its pages. Every interactive or selected state uses the primary, so the interface reads as one system.
* **Type.** Barlow Condensed in title case for headlines and numerals, the way scoreboards and bibs set numbers; Inter for reading, set slightly tight at 14.5 px. Uppercase is kept for small labels only.
* **Surfaces.** Hairline borders instead of drop shadows, small corner radii (3 to 10 px) instead of round pills, and solid sticky bars, so pages read crisp, like a printed race programme. Hover states change a border, not a shadow.
* **Small details, used as interface.**
  * A start line under the words "start line": a short tick, then a rule that paints itself out from it on load.
  * Typographic dates on event rows.
  * A lane line in the sport's colour that runs in when you hover a row.
  * Match scores as small laps that fill with the score.
  * The readiness gauge as a full lap run anticlockwise from the start line.
  * Month headings sitting on a chalk line.
  * Registration confirmed as a race bib with safety-pin holes.
  * A race-card strip of key facts.
  * Course-profile glyphs.
* **A 13-icon sport set** drawn on a 24 px grid, so it sits naturally next to the Phosphor UI icons.
* **Explanations everywhere.** Every recommendation says why; every estimate says how it was made and that it is an estimate.
* **Responsive** down to 360 px, with a bottom tab bar on phones.

## 20. Honest limitations

* **Expected dates.** 75 events have dates inferred from previous editions. They are clearly marked, and the organiser site is linked.
* **Registration.** StartLine keeps your place in your season plan and issues a bib, but payment, timing chips and official start lists stay with the organiser. The confirmation says so and links to the official entry.
* **Weather.** Conditions come from long-term monthly normals, not a forecast.
* **The EKS cluster is not left running.** It costs about USD 0.30 an hour, so it is created for demos with `terraform/aws.sh` and destroyed after. While it is down, the `AWS_DEPLOY_ROLE_ARN` variable is removed and the deploy job skips with a notice; locally the same script deploys to kind.

## 21. Grading rubric: where each item is

Every criterion of the Session 21 rubric, with the file, command or screenshot that shows it.

| Rubric item | Evidence |
|---|---|
| **M1** FastAPI responds to `/health` | [routers/meta.py](backend/app/routers/meta.py) (`/health`, `/ready`), [output.md](output.md#8-kubernetes-and-ingress) |
| **M1** At least 4 REST endpoints with GET, POST, PUT, DELETE | 26 endpoints in [section 6](#6-api), for example `PUT /api/athletes/{id}` and `DELETE /api/registrations/{code}`; [routers/](backend/app/routers/) |
| **M1** PostgreSQL with tables managed by Alembic | [0001_initial_schema.py](backend/alembic/versions/0001_initial_schema.py) (10 tables), applied on every start by [entrypoint.sh](backend/entrypoint.sh) |
| **M1** Frontend renders and calls the API | [frontend/src/lib/api.js](frontend/src/lib/api.js), screenshots at the top of this README |
| **M1** Responsive, usable UI | [app-mobile.jpg](screenshots/app-mobile.jpg), [section 19](#19-interface-design) |
| **M2** `pytest` passes | [pytest-v.png](screenshots/pytest-v.png): 52 passed |
| **M2** At least 5 tests over at least 3 endpoints | 52 tests in [backend/tests/](backend/tests/), hitting `/api/events`, `/api/registrations`, `/api/athletes`, `/api/stats`, `/api/sports`, `/api/cities` and more |
| **M2** Test database, not production | [conftest.py](backend/tests/conftest.py): a throwaway SQLite file seeded with the catalogue |
| **M2** `pytest.ini` / `conftest.py` | [backend/pytest.ini](backend/pytest.ini), [backend/tests/conftest.py](backend/tests/conftest.py) |
| **M3** Public GitHub repository | https://github.com/bypratyush/startline |
| **M3** Meaningful commit messages, 10+ commits | [commit history](https://github.com/bypratyush/startline/commits/main), [git-commits.jpg](screenshots/git-commits.jpg): one commit per feature or tool |
| **M3** `.gitignore` covers `.env`, `__pycache__`, `node_modules`, `.venv` | [.gitignore](.gitignore) |
| **M4** `backend/Dockerfile` builds | [backend/Dockerfile](backend/Dockerfile), [docker-compose-up-build.png](screenshots/docker-compose-up-build.png) |
| **M4** Frontend multi-stage (Node build, nginx runtime) | [frontend/Dockerfile](frontend/Dockerfile): `node:22-alpine` build stage, `nginx-unprivileged` runtime |
| **M4** Non-root images | backend `USER 10001`, frontend nginx uid 101 ([output.md](output.md#4-docker-images)) |
| **M4** `docker compose up --build` starts all three services | [docker-compose-up-build.png](screenshots/docker-compose-up-build.png), [docker-compose-ps.png](screenshots/docker-compose-ps.png), the app on localhost:3000: [app-discover.jpg](screenshots/app-discover.jpg) |
| **M5** Workflow file, runs on push to `main` | [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml) (`on: push: branches: [main]`), [Actions runs](https://github.com/bypratyush/startline/actions), [ci-run.jpg](screenshots/ci-run.jpg) |
| **M5** `pytest` job gates the build | `test` job; `build-scan-push` has `needs: test` |
| **M5** Frontend built in the pipeline | `npm ci` + `npm run build` in `test`, and the frontend image in `build-scan-push` |
| **M5** Images for both frontend and backend | `build-scan-push` matrix: backend, frontend |
| **M5** Pushed to GHCR | [startline-backend](https://github.com/bypratyush/startline/pkgs/container/startline-backend), [startline-frontend](https://github.com/bypratyush/startline/pkgs/container/startline-frontend), [ghcr-backend-versions.jpg](screenshots/ghcr-backend-versions.jpg) |
| **M5** Tags are the commit SHA, not `latest` | `tag=${GITHUB_SHA::7}` in the workflow |
| **M6** Trivy scans both images in CI | the "Trivy scan" step of each `build-scan-push` job: [backend](screenshots/ci-trivy-backend.jpg), [frontend](screenshots/ci-trivy-frontend.jpg) |
| **M6** Fails on HIGH or CRITICAL | `--severity HIGH,CRITICAL --exit-code 1`, no `--ignore-unfixed` |
| **M6** Explanation of the result and one CVE | [section 10](#10-security-scanning): what was scanned, the clean result, CVE-2026-76642 in Debian's util-linux |
| **M7** Valid HCL, `init`, `plan` | [terraform/](terraform/), [aws-terraform-plan.png](screenshots/aws-terraform-plan.png) (44 to add on AWS), [terraform-localstack-run.png](screenshots/terraform-localstack-run.png) |
| **M7** VPC with 2 public subnets, EKS with a worker node group, in ap-south-1 | AWS Console: [VPC subnets](screenshots/aws-console-vpc-subnets.jpg), [EKS cluster](screenshots/aws-console-eks.jpg), [nodes](screenshots/aws-console-eks-nodes.jpg); [section 11](#11-terraform-aws-vpc--eks) |
| **M7** `terraform destroy`, `terraform.tfvars.example` | [aws-terraform-destroy.png](screenshots/aws-terraform-destroy.png) (44 destroyed on AWS), [terraform.tfvars.example](terraform/terraform.tfvars.example) |
| **M8** `k8s/namespace.yaml` | [k8s/namespace.yaml](k8s/namespace.yaml) |
| **M8** Helm chart with `Chart.yaml`, `values.yaml`, templates | [helm/startline/](helm/startline/) |
| **M8** `helm upgrade --install` works | [helm-list.png](screenshots/helm-list.png), [helm-history.png](screenshots/helm-history.png) |
| **M8** Backend and frontend with 2+ replicas, all pods Running | [kubectl-get-pods.png](screenshots/kubectl-get-pods.png) |
| **M8** ClusterIP Services | [kubectl-get-svc.png](screenshots/kubectl-get-svc.png) |
| **M8** Ingress: `/` to frontend, `/api` to backend | [ingress.yaml](helm/startline/templates/ingress.yaml), [app-via-ingress.jpg](screenshots/app-via-ingress.jpg), [swagger-via-ingress.jpg](screenshots/swagger-via-ingress.jpg) |
| **M9** `/metrics` in Prometheus format | [curl-metrics.png](screenshots/curl-metrics.png) |
| **M9** Prometheus in the cluster, scraping the app | [prometheus-targets.jpg](screenshots/prometheus-targets.jpg), [ServiceMonitor](helm/startline/templates/servicemonitor.yaml) |
| **M9** Grafana with live application panels | http://grafana.localhost (Ingress), [grafana-dashboard-rush.jpg](screenshots/grafana-dashboard-rush.jpg), [dashboard JSON](monitoring/startline-dashboard.json) |
| **M9** Prometheus and Grafana Helm values | [monitoring/kube-prometheus-stack-values.yaml](monitoring/kube-prometheus-stack-values.yaml) |
| **M10** README explaining the app | this file |
| **M10** Live demo: commit, pipeline, deployment update | a push rolling EKS from `301bd07` to `7ebf977`: [ci-deploy-eks-update.jpg](screenshots/ci-deploy-eks-update.jpg), [aws-eks-deployment-update.png](screenshots/aws-eks-deployment-update.png); locally `./scripts/deploy.sh kind` ([section 9](#9-cicd-with-github-actions)) |

