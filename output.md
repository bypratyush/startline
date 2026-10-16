# StartLine: verified run log

> **Submitted by:** Pratyush Mohanty  |  **Roll No.:** 24BCS10238

Every block below is real output captured on 15 and 16 Oct 2026 on an Apple Silicon
Mac. The tools were Docker 29.6.1, a 3-node kind cluster running Kubernetes
1.37, Helm 4.3.0, Terraform 1.16.4, Python 3.13 and Node 22/25. Nothing was
typed in by hand. The screenshots in [screenshots/](screenshots/) come from
the same runs.

Contents: [seed](#1-seed-catalogue) · [tests](#2-backend-tests) · [compose](#3-docker-compose) ·
[images](#4-docker-images) · [trivy](#5-trivy) · [ci](#ci-test-job-run-locally-with-act) ·
[terraform](#7-terraform-on-localstack) · [kubernetes](#8-kubernetes-and-ingress) · [helm](#9-helm-upgrade-rollback-history) ·
[database](#10-database) · [prometheus](#11-prometheus) · [hpa](#hpa) · [alert](#13-alert-firing-during-an-outage) ·
[troubleshooting](#14-troubleshooting-lab)

## 1. Seed catalogue

```text
$ python3 research/build_seed.py
cities 36, sports 13, events 215
by sport: {'running': 76, 'triathlon': 21, 'cycling': 18, 'trail-running': 16, 'swimming': 15, 'tennis': 13, 'badminton': 11, 'fitness-racing': 9, 'ocr': 9, 'pickleball': 9, 'football': 7, 'squash': 7, 'table-tennis': 4}

$ cd backend && python -m app.seed --check
seed data OK: 36 cities, 13 sports, 215 events
```

## 2. Backend tests

```text
============================= test session starts ==============================
platform darwin -- Python 3.13.2, pytest-9.1.1, pluggy-1.6.0 -- /Users/pratyushmohanty/Downloads/startline/backend/.venv/bin/python
rootdir: /Users/pratyushmohanty/Downloads/startline/backend
configfile: pytest.ini
testpaths: tests
plugins: cov-7.1.0, anyio-4.15.1
collecting ... collected 52 items

tests/test_api.py::test_health_is_cheap_and_ready_checks_the_catalogue PASSED
tests/test_api.py::test_root_points_at_docs PASSED
tests/test_api.py::test_metrics_exposes_http_and_business_metrics PASSED
tests/test_api.py::test_every_sport_asks_two_or_three_required_questions PASSED
tests/test_api.py::test_cities_are_tier_1_and_2_only PASSED
tests/test_api.py::test_unknown_sport_is_404 PASSED
tests/test_api.py::test_profile_derives_level_from_answers PASSED
tests/test_api.py::test_profile_requires_every_question PASSED
tests/test_api.py::test_profile_rejects_unknown_answers_and_duplicate_sports PASSED
tests/test_api.py::test_patch_turns_recommendations_off PASSED
tests/test_api.py::test_put_replaces_sports PASSED
tests/test_api.py::test_discovery_puts_recommended_events_first PASSED
tests/test_api.py::test_beginner_swimmer_is_not_pushed_to_long_swims PASSED
tests/test_api.py::test_recommendations_can_be_switched_off PASSED
tests/test_api.py::test_filters_by_sport_city_radius_and_month PASSED
tests/test_api.py::test_search_matches_name_and_city PASSED
tests/test_api.py::test_event_detail_has_categories_weather_and_match PASSED
tests/test_api.py::test_guide_anchors_timeline_to_the_start PASSED
tests/test_api.py::test_calendar_export PASSED
tests/test_api.py::test_readiness_form_is_prefilled_from_profile PASSED
tests/test_api.py::test_stats PASSED
tests/test_api.py::test_saturated_db_pool_returns_503_not_500 PASSED
tests/test_engine.py::test_parse_duration PASSED
tests/test_engine.py::test_age_brackets_from_category_names PASSED
tests/test_engine.py::test_rating_and_format_parsing PASSED
tests/test_engine.py::test_triathlon_distance_classes PASSED
tests/test_engine.py::test_rated_draw_above_your_rating_is_ineligible PASSED
tests/test_engine.py::test_preferred_format_wins PASSED
tests/test_engine.py::test_kids_categories_are_never_picked_for_adults PASSED
tests/test_engine.py::test_first_triathlon_wording PASSED
tests/test_engine.py::test_riegel_matches_published_formula PASSED
tests/test_engine.py::test_trained_runner_is_ready_for_a_half PASSED
tests/test_engine.py::test_undertrained_runner_is_told_to_build_for_a_marathon PASSED
tests/test_engine.py::test_brevet_uses_acp_time_limit PASSED
tests/test_engine.py::test_triathlon_splits_add_up PASSED
tests/test_engine.py::test_court_readiness_reports_tournament_day_load PASSED
tests/test_engine.py::test_readiness_validates_inputs PASSED
tests/test_engine.py::test_heat_index_matches_nws_table PASSED
tests/test_engine.py::test_recovery_days_scale_with_distance PASSED
tests/test_engine.py::test_weeks_label_is_singular_for_one_week PASSED
tests/test_registrations.py::test_register_gets_a_bib_and_appears_in_season PASSED
tests/test_registrations.py::test_duplicate_registration_is_refused PASSED
tests/test_registrations.py::test_minimum_age_is_enforced_on_race_day PASSED
tests/test_registrations.py::test_bad_phone_and_missing_declaration_are_rejected PASSED
tests/test_registrations.py::test_closed_events_refuse_entries PASSED
tests/test_registrations.py::test_doubles_need_a_partner PASSED
tests/test_registrations.py::test_cancel_frees_the_category PASSED
tests/test_registrations.py::test_saved_events_and_recovery_warning PASSED
tests/test_seed.py::test_seed_files_validate PASSED
tests/test_seed.py::test_every_event_is_sourced_and_upcoming PASSED
tests/test_seed.py::test_no_em_dashes_in_text PASSED
tests/test_seed.py::test_seed_is_idempotent PASSED

============================== 52 passed in 0.63s ==============================
```

Coverage:

```text
--------------------------------------------------
app/catalog_cache.py              27      2    93%
app/config.py                     27      2    93%
app/db.py                         29      6    79%
app/deps.py                       33      3    91%
app/engine/__init__.py             0      0   100%
app/engine/categories.py          94      7    93%
app/engine/geo.py                  8      0   100%
app/engine/guide.py               81     19    77%
app/engine/profile.py             76      6    92%
app/engine/readiness.py          449    139    69%
app/engine/recommend.py          240     30    88%
app/engine/season.py              35      6    83%
app/main.py                       38      2    95%
app/models.py                    153      0   100%
app/observability.py              29      1    97%
app/routers/__init__.py            0      0   100%
app/routers/athletes.py          123     19    85%
app/routers/catalog.py            27      2    93%
app/routers/events.py            150      8    95%
app/routers/meta.py               36      4    89%
app/routers/readiness.py          28     15    46%
app/routers/registrations.py      73      9    88%
app/schemas.py                    71      1    99%
app/seed/__init__.py             135     34    75%
app/seed/__main__.py               3      3     0%
app/serializers.py                37      1    97%
--------------------------------------------------
TOTAL                           2002    319    84%
52 passed in 1.30s
```

## 3. Docker Compose

```text
$ docker compose ps
NAME                   IMAGE                COMMAND                  SERVICE    CREATED          STATUS                    PORTS
startline-backend-1    startline-backend    "./entrypoint.sh"        backend    2 minutes ago    Up 2 minutes (healthy)    0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
startline-db-1         postgres:17-alpine   "docker-entrypoint.s…"   db         29 minutes ago   Up 29 minutes (healthy)   127.0.0.1:5433->5432/tcp
startline-frontend-1   startline-frontend   "/docker-entrypoint.…"   frontend   6 minutes ago    Up 6 minutes              0.0.0.0:3000->8080/tcp, [::]:3000->8080/tcp

$ curl -s localhost:8000/ready
{"status":"ready","sports":13,"events":215}

$ curl -s -o /dev/null -w "%{http_code}" localhost:3000/   (React via nginx)
200

$ curl -s localhost:3000/api/sports | jq length   (nginx proxies /api to the backend)
13

$ docker compose logs backend | head
backend-1  | seeded 36 cities, 13 sports, 215 events (0 new), 812 categories
backend-1  | {"ts": "2026-10-15T01:02:21", "level": "INFO", "logger": "startline", "msg": "starting StartLine compose (compose)"}
backend-1  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## 4. Docker images

```text
$ docker image ls startline-*
REPOSITORY           TAG       IMAGE ID       SIZE
startline-backend    latest    8a4e3bf57c43   183MB
startline-backend    local     8a4e3bf57c43   183MB
startline-frontend   latest    9f427d969f18   114MB
startline-frontend   local     9f427d969f18   114MB

$ docker run --rm --entrypoint id startline-backend:local
uid=10001(app) gid=10001(app) groups=10001(app),10001(app)
$ docker run --rm --entrypoint id startline-frontend:local
uid=101(nginx) gid=101(nginx) groups=101(nginx),101(nginx)
```

## 5. Trivy

Both images, every HIGH and CRITICAL finding, fixed upstream or not, `--exit-code 1` (exit 0 = gate passed).


Frontend:

```text

Report Summary

┌──────────────────────────────────────────────┬────────┬─────────────────┐
│                    Target                    │  Type  │ Vulnerabilities │
├──────────────────────────────────────────────┼────────┼─────────────────┤
│ /scan/startline-frontend.tar (alpine 3.23.4) │ alpine │        0        │
└──────────────────────────────────────────────┴────────┴─────────────────┘
Legend:
- '-': Not scanned
- '0': Clean (no security findings detected)
```

Backend on python:3.13-alpine (OS layer and every Python package, all 0):

```text

Report Summary

┌──────────────────────────────────────────────────────────────────────────────────┬────────────┬─────────────────┐
│                                      Target                                      │    Type    │ Vulnerabilities │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
│ /scan/startline-backend.tar (alpine 3.24.2)                                      │   alpine   │        0        │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
│ opt/venv/lib/python3.13/site-packages/alembic-1.20.0.dist-info/METADATA          │ python-pkg │        0        │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
│ opt/venv/lib/python3.13/site-packages/annotated_doc-0.0.5.dist-info/METADATA     │ python-pkg │        0        │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
│ opt/venv/lib/python3.13/site-packages/annotated_types-0.8.0.dist-info/METADATA   │ python-pkg │        0        │
├──────────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
...
└──────────────────────────────────────────────────────────────────────────────────┴────────────┴─────────────────┘
Legend:
- '-': Not scanned
- '0': Clean (no security findings detected)
```

The same scan on the earlier python:3.13-slim (Debian 13) backend failed with 44 HIGH findings, all in Debian base packages and none fixed in Debian yet ([full report](security/reports/trivy-backend-debian-slim-before.txt)). Moving to Alpine cleared them:

```text
/scan/startline-backend.tar (debian 13.7)
=========================================
Total: 44 (HIGH: 44, CRITICAL: 0)

┌───────────────┬────────────────┬──────────┬──────────────┬───────────────────────────────────┬───────────────┬─────────────────────────────────────────────────────────────┐
│    Library    │ Vulnerability  │ Severity │    Status    │         Installed Version         │ Fixed Version │                            Title                            │
├───────────────┼────────────────┼──────────┼──────────────┼───────────────────────────────────┼───────────────┼─────────────────────────────────────────────────────────────┤
│ bsdutils      │ CVE-2026-76642 │ HIGH     │ affected     │ 1:2.41.5-0+deb13u1                │               │ util-linux: util-linux: failed external mount helper still  │
│               │                │          │              │                                   │               │ runs privileged X-mount post-hooks                          │
│               │                │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-76642                  │
│               ├────────────────┤          │              │                                   ├───────────────┼─────────────────────────────────────────────────────────────┤
│               │ CVE-2026-78408 │          │              │                                   │               │ util-linux: util-linux: nsenter --join-cgroup leaks root    │
│               │                │          │              │                                   │               │ cgroup migration authority                                  │
│               │                │          │              │                                   │               │ https://avd.aquasec.com/nvd/cve-2026-78408                  │
```

<a id="ci-test-job-run-locally-with-act"></a>
## 6. CI test job run locally with act

`act push -j test` on a throwaway Git copy of the repository, with the Postgres 17 service container. Step summary (full log: [ci-logs/act-test-job.log](ci-logs/act-test-job.log)):


```text
⭐ Run Main actions/checkout@v6
✅  Success - Main actions/checkout@v6 [188.059917ms]
⭐ Run Main actions/setup-python@v6
✅  Success - Main actions/setup-python@v6 [942.787416ms]
⭐ Run Main Install backend dependencies
✅  Success - Main Install backend dependencies [739.370875ms]
⭐ Run Main Lint (ruff check + ruff format --check)
✅  Success - Main Lint (ruff check + ruff format --check) [176.937667ms]
⭐ Run Main Seed catalogue is valid
| seed data OK: 36 cities, 13 sports, 215 events
✅  Success - Main Seed catalogue is valid [677.550625ms]
⭐ Run Main pytest with coverage (SQLite, see tests/conftest.py)
| TOTAL                           2002    319    84%
| 52 passed in 2.01s
✅  Success - Main pytest with coverage (SQLite, see tests/conftest.py) [3.112975334s]
⭐ Run Main Alembic upgrade / downgrade / upgrade on Postgres 17, then seed
| INFO  [alembic.runtime.migration] Running upgrade  -> 0001, initial schema: cities, sports, events, categories, athletes, registrations
| No new upgrade operations detected.
| INFO  [alembic.runtime.migration] Running downgrade 0001 -> , initial schema: cities, sports, events, categories, athletes, registrations
| INFO  [alembic.runtime.migration] Running upgrade  -> 0001, initial schema: cities, sports, events, categories, athletes, registrations
| seeded 36 cities, 13 sports, 215 events (215 new), 812 categories
✅  Success - Main Alembic upgrade / downgrade / upgrade on Postgres 17, then seed [4.614847125s]
⭐ Run Main Upload test report
✅  Success - Main Upload test report [1.641617s]
⭐ Run Main actions/setup-node@v6
✅  Success - Main actions/setup-node@v6 [2.406888542s]
⭐ Run Main Frontend build
| dist/assets/index-fI1qN_T3.css                                      61.45 kB │ gzip:  12.71 kB
| dist/assets/index-DvtQaS5z.js                                      433.08 kB │ gzip: 124.47 kB
| ✓ built in 717ms
✅  Success - Main Frontend build [6.57087125s]
🏁  Job succeeded
```

## 7. Terraform on LocalStack

`./terraform/run.sh`


```text
== LocalStack
localstack up on :4568
Success! The configuration is valid.

== plan with the EKS cluster (design check, not applied: LocalStack Community has no EKS)
Plan: 44 to add, 0 to change, 0 to destroy.
   1 x aws_eip
   1 x aws_eks_access_entry
   1 x aws_eks_access_policy_association
   6 x aws_eks_addon
   1 x aws_eks_cluster
   1 x aws_eks_node_group
   1 x aws_iam_openid_connect_provider
   4 x aws_iam_role
   1 x aws_iam_role_policy
   5 x aws_iam_role_policy_attachment
   1 x aws_internet_gateway
   1 x aws_launch_template
   1 x aws_nat_gateway
   2 x aws_route
   3 x aws_route_table
   4 x aws_route_table_association
   1 x aws_security_group
   4 x aws_subnet
   1 x aws_vpc
   1 x aws_vpc_security_group_egress_rule
   3 x aws_vpc_security_group_ingress_rule
== apply the network and IAM (enable_eks = false)
Apply complete! Resources: 29 added, 0 changed, 0 destroyed.
configure_kubectl = "enable_eks = false: no cluster created"
github_deploy_role_arn = "arn:aws:iam::000000000000:role/startline-github-deploy"
nat_gateway_public_ips = []
node_security_group_id = "sg-fcab9f07809e0029e"
private_subnet_ids = [
  "subnet-96a5874088a473e07",
  "subnet-c3c79ef0459d64829",
]
public_subnet_ids = [
  "subnet-8fe3bca5fd24df71c",
  "subnet-2af14dc43935739fe",
]
vpc_id = "vpc-218970c6ae3f33c2d"
== what exists now (AWS CLI against LocalStack)
-------------------------------------------
|              DescribeVpcs               |
+---------------+-------------------------+
|     Cidr      |           Vpc           |
+---------------+-------------------------+
|  10.40.0.0/16 |  vpc-218970c6ae3f33c2d  |
+---------------+-------------------------+
-------------------------------------------------------------------------------
|                               DescribeSubnets                               |
+-------------+----------------+---------------------------------+------------+
|     AZ      |     Cidr       |              Name               | PublicIp   |
+-------------+----------------+---------------------------------+------------+
|  ap-south-1a|  10.40.1.0/24  |  startline-public-ap-south-1a   |  True      |
|  ap-south-1a|  10.40.11.0/24 |  startline-private-ap-south-1a  |  False     |
|  ap-south-1b|  10.40.12.0/24 |  startline-private-ap-south-1b  |  False     |
|  ap-south-1b|  10.40.2.0/24  |  startline-public-ap-south-1b   |  True      |
+-------------+----------------+---------------------------------+------------+
-----------------------------------------------------------
|                   DescribeRouteTables                   |
+-----------------------------------+---------+-----------+
|               Name                | Routes  |  Subnets  |
+-----------------------------------+---------+-----------+
|  None                             |  1      |  1        |
|  startline-private-rt-ap-south-1b |  1      |  1        |
|  startline-private-rt-ap-south-1a |  1      |  1        |
|  startline-public-rt              |  2      |  2        |
+-----------------------------------+---------+-----------+
-----------------------------
|         ListRoles         |
+---------------------------+
|           Role            |
+---------------------------+
|  startline-eks-nodes      |
|  startline-ebs-csi        |
|  startline-github-deploy  |
|  startline-eks-cluster    |
+---------------------------+
== destroy
Destroy complete! Resources: 29 destroyed.
localstack removed
```

## 8. Kubernetes and Ingress

```text
$ kubectl get nodes
NAME                      STATUS   ROLES           AGE   VERSION
devops-hw-control-plane   Ready    control-plane   28d   v1.37.0
devops-hw-worker          Ready    <none>          28d   v1.37.0
devops-hw-worker2         Ready    <none>          28d   v1.37.0

$ kubectl get pods,svc,hpa,ingress,pvc,pdb -n startline
NAME                                      READY   STATUS    RESTARTS      AGE
pod/startline-backend-79bd46d4b8-7vssw    1/1     Running   0             7m43s
pod/startline-backend-79bd46d4b8-d7q2g    1/1     Running   0             7m37s
pod/startline-db-0                        1/1     Running   2 (66m ago)   36h
pod/startline-frontend-794c5b76b4-nc2pm   1/1     Running   0             7m37s
pod/startline-frontend-794c5b76b4-txc6c   1/1     Running   0             7m43s

NAME                         TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
service/startline-backend    ClusterIP   10.96.103.147   <none>        8000/TCP   36h
service/startline-db         ClusterIP   None            <none>        5432/TCP   36h
service/startline-frontend   ClusterIP   10.96.253.0     <none>        80/TCP     36h

NAME                                                    REFERENCE                      TARGETS       MINPODS   MAXPODS   REPLICAS   AGE
horizontalpodautoscaler.autoscaling/startline-backend   Deployment/startline-backend   cpu: 4%/60%   2         6         2          36h

NAME                                  CLASS   HOSTS                                 ADDRESS     PORTS   AGE
ingress.networking.k8s.io/startline   nginx   startline.local,startline.localhost   localhost   80      36h

NAME                                        STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
persistentvolumeclaim/data-startline-db-0   Bound    pvc-7fc60706-b2dd-44fd-a158-b14d414bd148   1Gi        RWO            standard       <unset>                 36h

NAME                                           MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
poddisruptionbudget.policy/startline-backend   1               N/A               1                     36h

$ helm list -n startline
NAME     	NAMESPACE	REVISION	UPDATED                             	STATUS  	CHART          	APP VERSION
startline	startline	7       	2026-10-16 18:36:20.403326 +0530 IST	deployed	startline-1.0.0	1.0.0      

$ kubectl get ns startline --show-labels
NAME        STATUS   AGE   LABELS
startline   Active   36h   app.kubernetes.io/part-of=startline,kubernetes.io/metadata.name=startline,pod-security.kubernetes.io/enforce-version=latest,pod-security.kubernetes.io/enforce=restricted

$ kubectl top pods -n startline
NAME                                  CPU(cores)   MEMORY(bytes)   
startline-backend-79bd46d4b8-7vssw    5m           85Mi            
startline-backend-79bd46d4b8-d7q2g    4m           74Mi            
startline-db-0                        9m           30Mi            
startline-frontend-794c5b76b4-nc2pm   1m           17Mi            
startline-frontend-794c5b76b4-txc6c   1m           14Mi            

$ curl -s -H "Host: startline.local" http://localhost/api/stats
{'events_upcoming': 215, 'events_next_30_days': 51, 'cities': 36, 'cities_with_events': 29, 'sports': 13, 'athletes': 4, 'registrations': 3}

$ curl -s -o /dev/null -w "%{http_code}" -H "Host: startline.local" http://localhost/        (React, via Ingress)
200
$ curl -s -o /dev/null -w "%{http_code}" -H "Host: startline.local" http://localhost/docs    (Swagger, via Ingress)
200
$ kubectl -n startline exec deploy/startline-backend -- python -c (GET http://127.0.0.1:8000/ready)
{"status":"ready","sports":13,"events":215}
```

## 9. Helm upgrade, rollback, history

Upgrade with a config change (revision 3), roll back to 2 (revision 4), then two chart fixes found along the way (revisions 5 and 6).


```text
$ helm list -n startline
NAME     	NAMESPACE	REVISION	UPDATED                             	STATUS  	CHART          	APP VERSION
startline	startline	2       	2026-10-15 06:18:50.186965 +0530 IST	deployed	startline-1.0.0	1.0.0      

$ helm upgrade startline ./helm/startline -n startline -f helm/startline/values-dev.yaml --set config.logLevel=DEBUG --wait
I1015 06:31:14.921013   17100 warnings.go:107] "Warning: path /openapi.json cannot be used with pathType Prefix"
STATUS: deployed
REVISION: 3

$ kubectl -n startline get configmap startline-config -o jsonpath={.data.LOG_LEVEL}
DEBUG

$ helm history startline -n startline
REVISION	UPDATED                 	STATUS    	CHART          	APP VERSION	DESCRIPTION     
1       	Thu Oct 15 06:09:05 2026	superseded	startline-1.0.0	1.0.0      	Install complete
2       	Thu Oct 15 06:18:50 2026	superseded	startline-1.0.0	1.0.0      	Upgrade complete
3       	Thu Oct 15 06:31:14 2026	deployed  	startline-1.0.0	1.0.0      	Upgrade complete
$ helm rollback startline 2 -n startline --wait
I1015 06:31:37.633061   19020 warnings.go:107] "Warning: path /openapi.json cannot be used with pathType Prefix"
Rollback was a success! Happy Helming!

$ kubectl -n startline get configmap startline-config -o jsonpath={.data.LOG_LEVEL}
INFO

# chart fix: /openapi.json uses pathType Exact (ingress-nginx warned about Prefix)
$ helm upgrade startline ./helm/startline -n startline -f helm/startline/values-dev.yaml --wait
I1015 06:31:50.879051   20103 warnings.go:107] "Warning: path /openapi.json cannot be used with pathType Exact"
STATUS: deployed
REVISION: 5

$ helm history startline -n startline
REVISION	UPDATED                 	STATUS    	CHART          	APP VERSION	DESCRIPTION     
1       	Thu Oct 15 06:09:05 2026	superseded	startline-1.0.0	1.0.0      	Install complete
2       	Thu Oct 15 06:18:50 2026	superseded	startline-1.0.0	1.0.0      	Upgrade complete
3       	Thu Oct 15 06:31:14 2026	superseded	startline-1.0.0	1.0.0      	Upgrade complete
4       	Thu Oct 15 06:31:37 2026	superseded	startline-1.0.0	1.0.0      	Rollback to 2   
5       	Thu Oct 15 06:31:50 2026	deployed  	startline-1.0.0	1.0.0      	Upgrade complete

# chart fix: serve the OpenAPI schema under /api, drop the extra /openapi.json path
$ helm upgrade startline ./helm/startline -n startline -f helm/startline/values-dev.yaml --wait
STATUS: deployed
REVISION: 6
```

## 10. Database

```text
$ kubectl -n startline exec startline-db-0 -- psql -U startline -d startline -c "\dt"
               List of relations
 Schema |       Name       | Type  |   Owner   
--------+------------------+-------+-----------
 public | alembic_version  | table | startline
 public | athlete_sports   | table | startline
 public | athletes         | table | startline
 public | cities           | table | startline
 public | event_categories | table | startline
 public | events           | table | startline
 public | readiness_checks | table | startline
 public | registrations    | table | startline
 public | saved_events     | table | startline
 public | sports           | table | startline
(10 rows)

$ ... -c "select s.name as sport, count(e.id) as events from sports s join events e on e.sport_id = s.id group by s.name, s.sort_order order by s.sort_order;"
      sport      | events 
-----------------+--------
 Road running    |     76
 Trail & ultra   |     16
 Cycling         |     18
 Swimming        |     15
 Triathlon       |     21
 Fitness racing  |      9
 Obstacle racing |      9
 Badminton       |     11
 Tennis          |     13
 Pickleball      |      9
 Table tennis    |      4
 Squash          |      7
 Football        |      7
(13 rows)

$ ... -c "select r.code, r.bib_number, r.full_name, c.name as category, e.name as event, r.status from registrations r join event_categories c on c.id = r.category_id join events e on e.id = r.event_id order by r.id;"
    code    | bib_number |    full_name     |   category    |                 event                  |  status   
------------+------------+------------------+---------------+----------------------------------------+-----------
 SL127-1001 |       1001 | Pratyush Mohanty | Open 10K      | TCS World 10K Bengaluru                | confirmed
 SL104-1001 |       1001 | Pratyush Mohanty | Half Marathon | Tata Mumbai Marathon                   | confirmed
 SL147-1001 |       1001 | Metrics Demo     | 1K Swim       | The Goa Swimathon (Racing at AquaMoga) | confirmed
(3 rows)

$ ... -c "select version_num from alembic_version;"
 version_num 
-------------
 0001
(1 row)
```

## 11. Prometheus

```text
$ curl -s localhost:9090/api/v1/targets (job=startline-backend)
startline-backend-6cf7f5d67b-crxmb up http://10.244.2.29:8000/metrics
startline-backend-6cf7f5d67b-dhgk4 up http://10.244.1.42:8000/metrics

$ curl -s localhost:9090/api/v1/rules (StartLine groups)
startline.availability | StartLineBackendDown | inactive
startline.availability | StartLineDatabaseUnreachable | inactive
startline.slo | StartLineHighErrorRate | inactive
startline.slo | StartLineSlowEventSearch | inactive
startline.slo | StartLineAutoscalerMaxed | inactive

$ curl -s localhost:9090/api/v1/query (business metrics after a few real requests through the Ingress)
  sum by (sport, city_tier) (startline_registrations_total)
     {'city_tier': '2', 'sport': 'swimming'} 1
  sum by (sport, verdict) (startline_readiness_checks_total)
     {'sport': 'cycling', 'verdict': 'ready'} 2
     {'sport': 'swimming', 'verdict': 'nearly'} 1
     {'sport': 'swimming', 'verdict': 'not-this-one'} 1
  sum by (recommendations) (startline_event_searches_total)
     {'recommendations': 'on'} 5
     {'recommendations': 'off'} 3
     {'recommendations': 'no-profile'} 3
  max(startline_db_up)
     {} 1
  sum by (handler, status) (startline_http_requests_total{handler=~"/api/(events|readiness|registrations|athletes)"})
     {'handler': '/api/events', 'status': '200'} 11
     {'handler': '/api/readiness', 'status': '200'} 4
     {'handler': '/api/registrations', 'status': '201'} 1
     {'handler': '/api/athletes', 'status': '201'} 1
```

<a id="hpa"></a>
## 12. HPA under a registration rush

`./scripts/registration-rush.sh`: 3 load pods x 8 workers searching events with recommendations on, 3 minutes.

**First run** (before the fixes):


```text
rush started at 06:11:18: watching the HPA every 15 s
TIME      CPU (avg / target)          REPLICAS
06:11:18  5% / 60%                    2
06:11:33  7% / 60%                    2
06:11:48  5% / 60%                    2
06:12:04  <none>% / 60%               2
06:12:19  <none>% / 60%               2
06:12:34  <none>% / 60%               2
06:12:49  <none>% / 60%               2
06:13:05  <none>% / 60%               2
06:13:20  <none>% / 60%               2
06:13:35  <none>% / 60%               2
06:13:50  <none>% / 60%               2
06:14:05  500% / 60%                  2
06:14:20  483% / 60%                  4
06:14:35  411% / 60%                  6
06:14:50  382% / 60%                  6
06:15:05  222% / 60%                  6
06:15:20  30% / 60%                   6
06:15:35  28% / 60%                   6
06:15:51  22% / 60%                   6
06:16:06  20% / 60%                   6
06:16:21  13% / 60%                   3
06:16:36  10% / 60%                   3
06:16:51  6% / 60%                    3
06:17:06  5% / 60%                    2
  requests=691 errors=9 avg_latency=2064ms
  requests=699 errors=9 avg_latency=2077ms
done {"ok": 693, "err": 9, "latency": 1452.1822118850123}
```

Errors behind the first run, from the backend logs:

```text
$ curl -s localhost:9090/api/v1/query --data-urlencode 'query=sum by (status, handler) (increase(startline_http_requests_total{job="startline-backend",status!~"2.."}[30m]))'
{'handler': '/api/events', 'status': '500'} 33.9

$ for p in $(kubectl -n startline get pods -l app.kubernetes.io/component=backend -o name); do kubectl -n startline logs $p | grep -E "Error|Exception|Traceback" | sort | uniq -c | sort -rn | head; done
  39 Traceback (most recent call last):
  39 sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 5 reached, connection timed out, timeout 30.00 (Background on this error at: https://sqlalche.me/e/21/3o7r)
  39 ERROR:    Exception in ASGI application

$ kubectl -n startline describe hpa startline-backend | sed -n '/Events:/,$p'
  Warning  FailedGetResourceMetric       3m50s (x11 over 7m50s)  horizontal-pod-autoscaler  failed to get cpu utilization: did not receive metrics for targeted pods (pods might be unready)
  Normal   SuccessfulRescale             3m35s                   horizontal-pod-autoscaler  New size: 4; reason: cpu resource utilization (percentage of request) above target
  Normal   SuccessfulRescale             3m19s                   horizontal-pod-autoscaler  New size: 6; reason: cpu resource utilization (percentage of request) above target
  Normal   SuccessfulRescale             94s                     horizontal-pod-autoscaler  New size: 3; reason: All metrics below target
  Normal   SuccessfulRescale             49s                     horizontal-pod-autoscaler  New size: 2; reason: All metrics below target
```

**After the fixes** (catalogue cache, connection released before scoring, pool 5 + 10 with a 503 when saturated, 3 s probe timeouts):


```text
rush started at 06:24:37: watching the HPA every 15 s
TIME      CPU (avg / target)          REPLICAS
06:24:37  3% / 60%                    2
06:24:52  <none>% / 60%               2
06:25:07  221% / 60%                  2
06:25:22  291% / 60%                  4
06:25:37  352% / 60%                  6
06:25:52  420% / 60%                  6
06:26:07  371% / 60%                  6
06:26:23  377% / 60%                  6
06:26:38  375% / 60%                  6
06:26:53  353% / 60%                  6
06:27:08  378% / 60%                  6
06:27:23  369% / 60%                  6
06:27:38  392% / 60%                  6
06:27:53  399% / 60%                  6
06:28:08  232% / 60%                  6
06:28:24  12% / 60%                   6
06:28:39  15% / 60%                   6
06:28:54  31% / 60%                   6
06:29:09  12% / 60%                   6
06:29:24  3% / 60%                    4
06:29:39  3% / 60%                    4
06:29:54  3% / 60%                    4
06:30:09  4% / 60%                    2
06:30:24  4% / 60%                    2
  requests=6490 errors=0 avg_latency=222ms
  requests=6494 errors=0 avg_latency=222ms
done {"ok": 6497, "err": 0, "latency": 1440.2209161109768}
```

Load generator totals and the server-side status codes for `/api/events`:

```text
$ for p in $(kubectl -n startline get pods -l job-name=startline-rush -o name); do kubectl -n startline logs $p | grep done; done
done {"ok": 6497, "err": 0, "latency": 1440.2209161109768}
done {"ok": 6423, "err": 0, "latency": 1440.724809167934}
done {"ok": 6459, "err": 0, "latency": 1440.3327625740203}
(19,379 requests, 0 errors, about 222 ms average latency per request)

$ curl -s localhost:9090/api/v1/query --data-urlencode 'query=sum by (status) (increase(startline_http_requests_total{job="startline-backend",handler="/api/events"}[6m]))'
{'status': '200'} 18101
{'status': '500'} 0
```

## 13. Alert firing during an outage

Scale the API to zero and watch `StartLineBackendDown` go pending, then firing, then resolve.


```text
$ kubectl -n startline scale deployment startline-backend --replicas=0
deployment.apps/startline-backend scaled
06:34:00  no StartLine alerts
06:34:15  StartLineBackendDown=pending
06:34:30  StartLineBackendDown=pending
06:34:46  StartLineBackendDown=pending
06:35:01  StartLineBackendDown=pending
06:35:16  StartLineBackendDown=firing
06:35:31  StartLineBackendDown=firing
06:35:46  StartLineBackendDown=firing
06:36:01  StartLineBackendDown=firing
06:36:16  StartLineBackendDown=firing

$ kubectl -n startline scale deployment startline-backend --replicas=2
deployment.apps/startline-backend scaled
Waiting for deployment "startline-backend" rollout to finish: 0 of 2 updated replicas are available...
Waiting for deployment "startline-backend" rollout to finish: 1 of 2 updated replicas are available...
deployment "startline-backend" successfully rolled out
06:36:38  StartLineBackendDown=pending
06:36:53  StartLineDatabaseUnreachable=pending
06:37:08  no StartLine alerts
06:37:23  no StartLine alerts
06:37:38  no StartLine alerts
06:37:53  no StartLine alerts

# finding: right after the restore, StartLineDatabaseUnreachable went "pending" for one scrape.
# cause: the startline_db_up gauge starts at 0 and was only set by the first readiness probe.
# fix: the API sets it from a real DB check at startup (app/main.py lifespan). Rolling restart after the fix:
$ kubectl -n startline rollout restart deployment/startline-backend && (alerts every 15 s)
deployment "startline-backend" successfully rolled out
no StartLine alerts
no StartLine alerts
no StartLine alerts
no StartLine alerts
no StartLine alerts
no StartLine alerts
```

## 14. Troubleshooting lab

`./troubleshooting/run.sh`


```text
================ FAULT 1: broken image ================
deployment.apps/startline-canary created
$ kubectl -n startline get pods -l app.kubernetes.io/name=startline-canary
NAME                                READY   STATUS             RESTARTS   AGE
startline-canary-68dc86979b-794p4   0/1     ImagePullBackOff   0          20s

$ kubectl -n startline describe pod/startline-canary-68dc86979b-794p4 | sed -n '/Containers:/,/Ready:/p;/Events:/,$p'
Containers:
  backend:
    Container ID:   
    Image:          startline-backend:v2.0-final
    Image ID:       
    Port:           8000/TCP
    Host Port:      0/TCP
    State:          Waiting
      Reason:       ImagePullBackOff
    Ready:          False
Events:
  Type     Reason     Age               From               Message
  ----     ------     ----              ----               -------
  Normal   Scheduled  20s               default-scheduler  Successfully assigned startline/startline-canary-68dc86979b-794p4 to devops-hw-worker2
  Normal   BackOff    17s               kubelet            spec.containers{backend}: Back-off pulling image "startline-backend:v2.0-final"
  Warning  Failed     17s               kubelet            spec.containers{backend}: Error: ImagePullBackOff
  Normal   Pulling    3s (x2 over 19s)  kubelet            spec.containers{backend}: Pulling image "startline-backend:v2.0-final"
  Warning  Failed     2s (x2 over 17s)  kubelet            spec.containers{backend}: Failed to pull image "startline-backend:v2.0-final": rpc error: code = NotFound desc = failed to pull and unpack image "docker.io/library/startline-backend:v2.0-final": failed to resolve reference "docker.io/library/startline-backend:v2.0-final": docker.io/library/startline-backend:v2.0-final: not found
  Warning  Failed     2s (x2 over 17s)  kubelet            spec.containers{backend}: Error: ErrImagePull

$ kubectl -n startline get events --sort-by=.lastTimestamp --field-selector involvedObject.name=startline-canary-68dc86979b-794p4 | tail -5
17s         Normal    BackOff     pod/startline-canary-68dc86979b-794p4   Back-off pulling image "startline-backend:v2.0-final"
17s         Warning   Failed      pod/startline-canary-68dc86979b-794p4   Error: ImagePullBackOff
3s          Normal    Pulling     pod/startline-canary-68dc86979b-794p4   Pulling image "startline-backend:v2.0-final"
2s          Warning   Failed      pod/startline-canary-68dc86979b-794p4   Failed to pull image "startline-backend:v2.0-final": rpc error: code = NotFound desc = failed to pull and unpack image "docker.io/library/startline-backend:v2.0-final": failed to resolve reference "docker.io/library/startline-backend:v2.0-final": docker.io/library/startline-backend:v2.0-final: not found
2s          Warning   Failed      pod/startline-canary-68dc86979b-794p4   Error: ErrImagePull

# diagnosis: the tag startline-backend:v2.0-final does not exist in any registry the nodes can reach.
# fix: point the Deployment at an image that was actually built (CI tags = commit SHA).
$ kubectl -n startline set image deployment/startline-canary backend=startline-backend:local
deployment.apps/startline-canary image updated

$ kubectl -n startline rollout status deployment/startline-canary --timeout=90s
Waiting for deployment "startline-canary" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "startline-canary" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "startline-canary" rollout to finish: 1 old replicas are pending termination...
deployment "startline-canary" successfully rolled out

$ kubectl -n startline get pods -l app.kubernetes.io/name=startline-canary
NAME                                READY   STATUS        RESTARTS   AGE
startline-canary-56989cb4c8-jj2dg   1/1     Running       0          1s
startline-canary-68dc86979b-794p4   0/1     Terminating   0          21s

================ FAULT 2: Service with no endpoints ================
service/startline-api created
$ kubectl -n startline get svc startline-api
NAME            TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
startline-api   ClusterIP   10.96.206.148   <none>        8000/TCP   0s

$ kubectl -n startline get endpointslices -l kubernetes.io/service-name=startline-api
NAME                  ADDRESSTYPE   PORTS     ENDPOINTS   AGE
startline-api-2xflk   IPv4          <unset>   <unset>     0s

$ kubectl -n startline run probe --rm -i --restart=Never --image=startline-backend:local -- (GET http://startline-api:8000/health)
request failed: <urlopen error [Errno 111] Connection refused>

$ kubectl -n startline get svc startline-api -o jsonpath={.spec.selector}{"\n"}
{"app.kubernetes.io/component":"api","app.kubernetes.io/instance":"startline"}

$ kubectl -n startline get pods -l app.kubernetes.io/component=backend --show-labels
NAME                                 READY   STATUS    RESTARTS   AGE     LABELS
startline-backend-799546dfb8-4hcpx   1/1     Running   0          6m7s    app.kubernetes.io/component=backend,app.kubernetes.io/instance=startline,app.kubernetes.io/name=startline,pod-template-hash=799546dfb8
startline-backend-799546dfb8-xswrj   1/1     Running   0          5m27s   app.kubernetes.io/component=backend,app.kubernetes.io/instance=startline,app.kubernetes.io/name=startline,pod-template-hash=799546dfb8

# diagnosis: the selector asks for component=api; the pods are labelled component=backend.
# fix: make the selector match the pod labels.
$ kubectl -n startline patch svc startline-api --type merge -p {"spec":{"selector":{"app.kubernetes.io/component":"backend"}}}
service/startline-api patched

$ kubectl -n startline get endpointslices -l kubernetes.io/service-name=startline-api
NAME                  ADDRESSTYPE   PORTS   ENDPOINTS                 AGE
startline-api-2xflk   IPv4          8000    10.244.2.21,10.244.1.27   6s

================ FAULT 3: Running but never Ready ================
deployment.apps/startline-backend-misconfigured created
$ kubectl -n startline get pods -l app.kubernetes.io/name=startline-backend-misconfigured
NAME                                               READY   STATUS    RESTARTS   AGE
startline-backend-misconfigured-5954595c5c-s9cxt   0/1     Running   0          30s

$ kubectl -n startline describe pod/startline-backend-misconfigured-5954595c5c-s9cxt | grep -A6 Events: (readiness events)
Events:
  Warning  Unhealthy  4s (x6 over 24s)  kubelet            spec.containers{backend}: Readiness probe failed: HTTP probe failed with statuscode: 503

$ kubectl -n startline exec pod/startline-backend-misconfigured-5954595c5c-s9cxt -- python -c (GET /health and /ready from inside the pod)
/health 200 {"status":"ok"}
/ready 503 {"status":"not-ready","reason":"OperationalError"}

# diagnosis: liveness (/health) passes, readiness (/ready) is 503 - the API cannot log in to Postgres.
# the DB_PASSWORD env var is a hard-coded literal instead of the Secret the real Deployment uses.
# fix: take the password from the Secret, exactly like the Helm chart does.
$ kubectl -n startline patch deployment startline-backend-misconfigured --type json -p [{"op":"replace","path":"/spec/template/spec/containers/0/env/0","value":{"name":"DB_PASSWORD","valueFrom":{"secretKeyRef":{"name":"startline-db","key":"DB_PASSWORD"}}}}]
deployment.apps/startline-backend-misconfigured patched

$ kubectl -n startline rollout status deployment/startline-backend-misconfigured --timeout=120s
Waiting for deployment "startline-backend-misconfigured" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "startline-backend-misconfigured" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "startline-backend-misconfigured" rollout to finish: 1 old replicas are pending termination...
deployment "startline-backend-misconfigured" successfully rolled out

$ kubectl -n startline get pods -l app.kubernetes.io/name=startline-backend-misconfigured
NAME                                               READY   STATUS        RESTARTS   AGE
startline-backend-misconfigured-5954595c5c-s9cxt   0/1     Terminating   0          37s
startline-backend-misconfigured-7fddbc66c-g8ccg    1/1     Running       0          6s
```
