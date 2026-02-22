# Kubernetes Security Audit Report

**Date:** 2026-02-23
**Cluster:** minikube — `https://127.0.0.1:59325`
**Auditor:** Senior K8s Security Auditor (Claude Agent — `k8s_audit` skill)
**Audit Stages:** Pre-flight · RBAC · Pod Security · Network Policies · Secret Management · CIS Benchmark

---

## Executive Summary

A comprehensive multi-stage security audit was performed against the Minikube cluster. All six audit stages
completed successfully. The cluster exhibits several severe misconfigurations typical of a development
environment that has not been hardened for production use.

| Severity | Count |
|----------|-------|
| 🔴 Critical | 4 |
| 🟠 High | 7 |
| 🟡 Medium | 8 |
| 🔵 Low / Informational | 3 |
| **Total Findings** | **22** |

> **Overall Risk Rating: HIGH** — Two Critical RBAC issues allow full cluster takeover, zero NetworkPolicies
> provide no east-west isolation, and API server audit logging is absent. Immediate remediation is required
> before this cluster is used for any sensitive workload.

---

## Table of Contents

1. [Pre-flight & Connectivity](#1-pre-flight--connectivity)
2. [RBAC Analysis](#2-rbac-analysis)
3. [Pod Security](#3-pod-security)
4. [Network Policies](#4-network-policies)
5. [Secret Management](#5-secret-management)
6. [CIS Benchmark Checks](#6-cis-benchmark-checks)
7. [Findings Summary & Remediation Roadmap](#7-findings-summary--remediation-roadmap)
8. [Appendix — Quick Remediation Snippets](#appendix--quick-remediation-snippets)

---

## 1. Pre-flight & Connectivity

| Check | Result |
|-------|--------|
| `kubectl cluster-info` | ✅ Reachable |
| API Server URL | `https://127.0.0.1:59325` |
| CoreDNS | ✅ Running |
| Total Namespaces | 7 |
| Total Pods Scanned | 16 |
| Total ServiceAccounts | 50+ |
| NetworkPolicies Found | **0** |
| ResourceQuotas Found | **0** |

```
Kubernetes control plane is running at https://127.0.0.1:59325
CoreDNS is running at https://127.0.0.1:59325/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
```

---

## 2. RBAC Analysis

### 2.1 🔴 CRITICAL — `kube-system/default` ServiceAccount Bound to `cluster-admin`

**Binding:** `minikube-rbac`
**Subject:** `ServiceAccount kube-system/default`
**Role:** `cluster-admin`

```
ClusterRoleBinding: minikube-rbac
  Role: cluster-admin  (verbs=[*]  resources=[*]  apiGroups=[*])
  Subject: kind=ServiceAccount  name=default  namespace=kube-system
```

The `default` service account in `kube-system` has unrestricted cluster-admin privileges. Any pod
running in `kube-system` with the default SA — or any attacker who reads its auto-mounted token —
can perform **any action** on any resource across the entire cluster. This is the highest-risk
finding in this audit.

**Remediation:**
```bash
kubectl delete clusterrolebinding minikube-rbac
# If kube-system/default requires specific permissions, create a dedicated SA and Role:
kubectl create serviceaccount minikube-operator -n kube-system
# Then bind only the minimum needed permissions
```

---

### 2.2 🔴 CRITICAL — User-Defined `kro-cluster-role` Has Full Wildcard Permissions

```
ClusterRole: kro-cluster-role
  verbs=['*']  resources=['*']  apiGroups=['*']
```

This **user-defined** role is functionally identical to `cluster-admin`. Any principal bound to
this role has full, unrestricted control of the cluster with no audit differentiation.

**Remediation:**
```bash
# Identify what is bound to this role
kubectl get clusterrolebindings,rolebindings --all-namespaces -o json | \
  python3 -c "import json,sys,itertools; data=json.load(sys.stdin); \
  [print(i['metadata']['name']) for i in data['items'] \
  if i.get('roleRef',{}).get('name')=='kro-cluster-role']"

# Replace with a scoped role limited to kro-system resources only
kubectl edit clusterrole kro-cluster-role
```

---

### 2.3 🔴 CRITICAL — `--anonymous-auth` Not Explicitly Disabled on API Server

```
--anonymous-auth  →  NOT SET (Kubernetes default = true)
```

When `--anonymous-auth` is not set to `false`, the API server accepts unauthenticated (anonymous)
requests. Although RBAC limits what anonymous users _can_ do, the attack surface is unnecessarily
broad and violates CIS Benchmark 1.2.1.

**Remediation:**
```yaml
# /etc/kubernetes/manifests/kube-apiserver.yaml
- --anonymous-auth=false
```

---

### 2.4 🔴 CRITICAL — No API Server Audit Logging (`--audit-log-path` Not Set)

```
--audit-log-path  →  NOT SET
```

Without audit logging, there is **zero forensic trail** of API calls. This makes it impossible to
detect credential theft, privilege escalation, or data exfiltration after the fact. Violates
CIS 1.2.18, SOC 2, and PCI-DSS requirements.

**Remediation:**
```yaml
# /etc/kubernetes/manifests/kube-apiserver.yaml
- --audit-log-path=/var/log/kubernetes/audit.log
- --audit-log-maxage=30
- --audit-log-maxbackup=10
- --audit-log-maxsize=100
- --audit-policy-file=/etc/kubernetes/audit-policy.yaml
```

---

### 2.5 🟠 HIGH — `cluster-admin` Bound to Broad System Groups

| Binding | Subject Kind | Subject Name | Risk |
|---------|-------------|--------------|------|
| `cluster-admin` | Group | `system:masters` | Every member gets unrestricted cluster control |
| `kubeadm:cluster-admins` | Group | `kubeadm:cluster-admins` | All kubeadm admin members have full cluster control |

**Remediation:**
- Audit and minimise membership of `system:masters` and `kubeadm:cluster-admins` groups.
- Prefer individual user bindings with namespace-scoped roles for day-to-day operations.
- Reserve `cluster-admin` for break-glass emergency access only.

---

### 2.6 🟡 MEDIUM — Built-in ClusterRoles Grant `secrets` Access

The following built-in ClusterRoles permit reading/writing `secrets`. While Kubernetes defaults,
their binding should be carefully audited:

| ClusterRole | Secrets Verbs |
|-------------|--------------|
| `admin` | `get, list, watch, create, delete, patch, update` |
| `edit` | `get, list, watch, create, delete, patch, update` |
| `system:aggregate-to-edit` | `get, list, watch, create, delete, patch, update` |
| `eg-gateway-helm-envoy-gateway-role` | `get, list, watch` |
| `system:node` | `get, list, watch` |

**Remediation:** Audit all RoleBindings that assign `admin` or `edit`. Create custom roles
that exclude `secrets` access where not required.

---

### 2.7 🟡 MEDIUM — Namespace Roles With Direct Secrets Access

| Namespace | Role | Secrets Verbs |
|-----------|------|--------------|
| `envoy-gateway-system` | `eg-gateway-helm-certgen` | `get, create, update` |
| `kube-system` | `system:controller:bootstrap-signer` | `get, list, watch` |
| `kube-system` | `system:controller:token-cleaner` | `delete, get, list, watch` |

**Remediation:** For `eg-gateway-helm-certgen`, scope to specific named secrets using
`resourceNames` and confirm the binding is removed after Helm install completes.

---

## 3. Pod Security

### 3.1 🟠 HIGH — Privileged Container: `kube-proxy`

| Namespace | Pod | Container | Finding |
|-----------|-----|-----------|---------|
| `kube-system` | `kube-proxy-kfdf4` | `kube-proxy` | `privileged: true` |

A privileged container has near-unrestricted access to the host kernel. While `kube-proxy`
requires elevated host networking access, running fully privileged widens the blast radius
of any container-level exploit.

**Remediation:**
```yaml
securityContext:
  privileged: false
  capabilities:
    add: ["NET_ADMIN", "NET_RAW"]
  seccompProfile:
    type: RuntimeDefault
```

---

### 3.2 🟠 HIGH — `hostNetwork: true` on Multiple System Pods

| Namespace | Pod | hostNetwork | hostPath Mounts |
|-----------|-----|-------------|----------------|
| `kube-system` | `etcd-minikube` | ✅ | `/var/lib/minikube/certs/etcd`, `/var/lib/minikube/etcd` |
| `kube-system` | `kube-apiserver-minikube` | ✅ | `/etc/ssl/certs`, `/etc/ca-certificates`, `/var/lib/minikube/certs` |
| `kube-system` | `kube-controller-manager-minikube` | ✅ | `/etc/ssl/certs`, `/var/lib/minikube/certs`, plus more |
| `kube-system` | `kube-proxy-kfdf4` | ✅ | `/run/xtables.lock`, `/lib/modules` |
| `kube-system` | `kube-scheduler-minikube` | ✅ | `/etc/kubernetes/scheduler.conf` |
| `kube-system` | `storage-provisioner` | ✅ | `/tmp` |

> **Note:** `hostNetwork` is expected for control-plane static pods. However, `storage-provisioner`
> using `hostNetwork` and mounting `/tmp` via `hostPath` is unnecessary and should be corrected.

**Remediation for `storage-provisioner`:**
```yaml
# Remove hostNetwork: true
# Replace hostPath /tmp with emptyDir:
volumes:
  - name: tmp
    emptyDir: {}
```

---

### 3.3 🟠 HIGH — No Pod Security Admission (PSA) Labels on Any Namespace

All 7 namespaces are missing `pod-security.kubernetes.io/enforce` labels, meaning any pod can
be scheduled with any security configuration — no enforcement, no auditing, no warnings.

| Namespace | Enforce | Audit | Warn |
|-----------|---------|-------|------|
| `default` | ❌ | ❌ | ❌ |
| `envoy-gateway-system` | ❌ | ❌ | ❌ |
| `game-2048` | ❌ | ❌ | ❌ |
| `kro-system` | ❌ | ❌ | ❌ |
| `kube-node-lease` | ❌ | ❌ | ❌ |
| `kube-public` | ❌ | ❌ | ❌ |
| `kube-system` | ❌ | ❌ | ❌ |

**Remediation:**
```bash
# Application namespaces → restricted
kubectl label namespace default \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/warn=restricted \
  pod-security.kubernetes.io/audit=restricted

# System namespace → privileged (control plane requirement)
kubectl label namespace kube-system \
  pod-security.kubernetes.io/enforce=privileged
```

---

### 3.4 🟡 MEDIUM — 12 Containers Without Any `securityContext`

Containers without a `securityContext` may run as root, with write access to the root filesystem,
and with all Linux capabilities enabled.

| Namespace | Pod | Container |
|-----------|-----|-----------|
| `default` | `backend-2-6648884cb-mpn68` | `backend-2` |
| `default` | `backend-77d4d5968-x9bll` | `backend` |
| `game-2048` | `deployment-2048-7bf64bccb7-b2lqk` | `app-2048` |
| `game-2048` | `deployment-2048-7bf64bccb7-jpn56` | `app-2048` |
| `game-2048` | `deployment-2048-7bf64bccb7-jzvbj` | `app-2048` |
| `game-2048` | `deployment-2048-7bf64bccb7-mxwkl` | `app-2048` |
| `game-2048` | `deployment-2048-7bf64bccb7-wj6m5` | `app-2048` |
| `kube-system` | `etcd-minikube` | `etcd` |
| `kube-system` | `kube-apiserver-minikube` | `kube-apiserver` |
| `kube-system` | `kube-controller-manager-minikube` | `kube-controller-manager` |
| `kube-system` | `kube-scheduler-minikube` | `kube-scheduler` |
| `kube-system` | `storage-provisioner` | `storage-provisioner` |

**Remediation (apply to all application containers):**
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
  seccompProfile:
    type: RuntimeDefault
```

---

### 3.5 🟡 MEDIUM — `game-2048` Pods Use `:latest` Image Tag

All 5 replicas of the `game-2048` deployment pull `public.ecr.aws/l6m2t8p7/docker-2048:latest`.
Using `:latest` is non-deterministic — a re-pull can deploy a different (potentially
malicious or broken) image without any change to the manifest.

| Namespace | Container | Image |
|-----------|-----------|-------|
| `game-2048` (×5) | `app-2048` | `public.ecr.aws/l6m2t8p7/docker-2048:latest` |

**Remediation:**
```bash
kubectl set image deployment/deployment-2048 \
  app-2048=public.ecr.aws/l6m2t8p7/docker-2048:<specific-semver-or-sha256> \
  -n game-2048
```

---

## 4. Network Policies

### 4.1 🔴 CRITICAL — Zero NetworkPolicies Exist Cluster-Wide

```
kubectl get networkpolicies --all-namespaces
→ No resources found
```

**Every pod can communicate with every other pod across all namespaces with no restriction.**
There is zero east-west traffic isolation. A single compromised container can freely reach:
- The Kubernetes API server
- etcd (if reachable on the pod network)
- Every other workload in every namespace

| Namespace | Default-Deny Ingress | Default-Deny Egress |
|-----------|---------------------|---------------------|
| `default` | ❌ Missing | ❌ Missing |
| `envoy-gateway-system` | ❌ Missing | ❌ Missing |
| `game-2048` | ❌ Missing | ❌ Missing |
| `kro-system` | ❌ Missing | ❌ Missing |
| `kube-node-lease` | ❌ Missing | ❌ Missing |
| `kube-public` | ❌ Missing | ❌ Missing |

**Remediation — deploy default-deny then selectively allow:**
```yaml
# Step 1: default-deny-all per namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: default   # repeat for each application namespace
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
---
# Step 2: allow required traffic only, e.g.:
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-backend-from-gateway
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: envoy-gateway-system
      ports:
        - port: 8080
```

---

## 5. Secret Management

### 5.1 ✅ No Plaintext Secrets in Environment Variables

No containers were found with sensitive values (passwords, tokens, API keys) directly embedded
as plaintext in environment variable `value` fields.

> **Best Practice Recommendation:** Secrets referenced via `secretKeyRef` should be evaluated
> for migration to an external secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager,
> External Secrets Operator) to enable automatic rotation and centralised audit trails.

---

### 5.2 🟡 MEDIUM — All 16 Pods Have `automountServiceAccountToken: true` (Default)

No pod or service account in the cluster explicitly opts out of auto-mounting service account
tokens. If a container is compromised, the attacker can use the mounted token to interact with
the Kubernetes API at the permission level of that service account.

**Highest-risk combinations (auto-mount + elevated SA permissions):**

| Namespace | Pod | Service Account | Risk |
|-----------|-----|----------------|------|
| `kube-system` | `etcd-minikube` | `default` | SA is `cluster-admin` via `minikube-rbac`! |
| `kube-system` | `kube-apiserver-minikube` | `default` | Same — full cluster control from token |
| `kube-system` | `kube-controller-manager-minikube` | `default` | Same |
| `kube-system` | `kube-scheduler-minikube` | `default` | Same |
| `kro-system` | `kro-599fbb69f8-4gxfv` | `kro` | Review kro SA permissions |
| `default` | `backend-*`, `backend-2-*` | `backend`, `backend-2` | Workload tokens exposed |
| `game-2048` | `deployment-2048-*` (×5) | `default` | No API access needed |

**Remediation:**
```yaml
# At the ServiceAccount level (affects all pods using this SA):
apiVersion: v1
kind: ServiceAccount
metadata:
  name: backend
  namespace: default
automountServiceAccountToken: false

# Or at the individual Pod/Deployment level:
spec:
  automountServiceAccountToken: false
```

---

### 5.3 🟡 MEDIUM — No ResourceQuotas on Any Namespace

No `ResourceQuota` objects exist in any namespace. A compromised or misbehaving workload can
consume all cluster CPU, memory, and API objects, causing a denial-of-service against other
workloads.

**Remediation:**
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: default-quota
  namespace: default
spec:
  hard:
    pods: "20"
    requests.cpu: "2"
    requests.memory: 4Gi
    limits.cpu: "4"
    limits.memory: 8Gi
    persistentvolumeclaims: "10"
    services: "10"
```

---

## 6. CIS Benchmark Checks

### 6.1 API Server Flag Audit (CIS Section 1.2)

| CIS ID | Flag / Setting | Observed Value | Status | Severity |
|--------|---------------|---------------|--------|----------|
| 1.2.1 | `--anonymous-auth` | Not set → defaults `true` | ❌ FAIL | 🔴 Critical |
| 1.2.6 | `--authorization-mode` | `Node,RBAC` | ✅ PASS | — |
| 1.2.18 | `--audit-log-path` | Not set | ❌ FAIL | 🔴 Critical |
| 1.2.22 | `--insecure-port` | Not present (disabled) | ✅ PASS | — |
| 1.2.24 | `--tls-cert-file` | `/var/lib/minikube/certs/apiserver.crt` | ✅ PASS | — |
| 1.2.10 | `--profiling` | Not set → defaults `true` | ⚠️ WARN | 🟠 High |

---

### 6.2 🟠 HIGH — API Profiling Not Disabled (`--profiling`)

```
--profiling  →  NOT SET (Kubernetes default = true)
```

The API server's profiling endpoint (`/debug/pprof`) is reachable. While it requires
authentication, it can leak sensitive memory contents and performance data. CIS 1.2.10
recommends explicitly disabling it.

**Remediation:**
```yaml
- --profiling=false   # on kube-apiserver
- --profiling=false   # on kube-controller-manager
- --profiling=false   # on kube-scheduler
```

---

### 6.3 🟠 HIGH — `cluster-admin` Bound to `system:masters` Group (CIS 5.1.1)

CIS Benchmark 5.1.1 recommends that cluster-admin access be restricted to break-glass emergency
use only. The `system:masters` group binding is permanent and cannot be removed via RBAC.

**Remediation:**
- Audit who can authenticate with `system:masters` group membership (certificate-based users).
- Use individual user bindings with namespace-scoped roles for routine operations.
- Rotate or invalidate certificates for users who no longer need cluster-admin access.

---

### 6.4 🟠 HIGH — CIS 5.1.5: Default Service Accounts Auto-Mount Tokens

```
kubectl get serviceaccounts --all-namespaces
→ ALL 50+ service accounts have automountServiceAccountToken=true (default)
```

CIS 5.1.5 states that default service accounts should not have auto-mounting enabled.
Kubernetes recommends setting `automountServiceAccountToken: false` on all `default`
service accounts and creating dedicated service accounts per workload.

**Remediation:**
```bash
for ns in default envoy-gateway-system game-2048 kro-system; do
  kubectl patch serviceaccount default -n "$ns" \
    -p '{"automountServiceAccountToken": false}'
done
```

---

### 6.5 🔵 INFORMATIONAL — Authorization Mode is `Node,RBAC` ✅

```
--authorization-mode=Node,RBAC
```
Compliant with CIS 1.2.6. Both `Node` (for kubelet) and `RBAC` authorization are active.

---

### 6.6 🔵 INFORMATIONAL — TLS Certificate Configured ✅

```
--tls-cert-file=/var/lib/minikube/certs/apiserver.crt
```
In-transit encryption for the API server is active.

---

### 6.7 🔵 INFORMATIONAL — Insecure Port Disabled ✅

```
--insecure-port  →  NOT PRESENT
```
The HTTP insecure port is not enabled. Compliant with CIS 1.2.22.

---

## 7. Findings Summary & Remediation Roadmap

### Complete Findings Table

| # | Severity | Category | Finding | Priority |
|---|----------|----------|---------|----------|
| 1 | 🔴 Critical | RBAC | `minikube-rbac` grants `cluster-admin` to `kube-system/default` SA | P0 — Immediate |
| 2 | 🔴 Critical | Network | Zero NetworkPolicies — all pods have unrestricted lateral movement | P0 — Immediate |
| 3 | 🔴 Critical | CIS 1.2.1 | `--anonymous-auth` not explicitly `false` | P0 — Immediate |
| 4 | 🔴 Critical | CIS 1.2.18 | No API server audit logging configured | P0 — Immediate |
| 5 | 🟠 High | RBAC | `kro-cluster-role` (user-defined) has full wildcard `[*]` permissions | P1 — This week |
| 6 | 🟠 High | RBAC | `system:masters` + `kubeadm:cluster-admins` groups bound to `cluster-admin` | P1 — This week |
| 7 | 🟠 High | Pod Security | `kube-proxy` running as `privileged: true` | P1 — This week |
| 8 | 🟠 High | Pod Security | No PSA labels — zero pod security enforcement cluster-wide | P1 — This week |
| 9 | 🟠 High | CIS 1.2.10 | `--profiling` not disabled on API server/controller-manager/scheduler | P1 — This week |
| 10 | 🟠 High | CIS 5.1.5 | All 50+ ServiceAccounts auto-mount tokens by default | P1 — This week |
| 11 | 🟠 High | Pod Security | `storage-provisioner` uses `hostNetwork` + `/tmp` `hostPath` unnecessarily | P1 — This week |
| 12 | 🟡 Medium | RBAC | Built-in `admin`/`edit` roles grant full `secrets` CRUD | P2 — This month |
| 13 | 🟡 Medium | RBAC | `eg-gateway-helm-certgen` role can create/update secrets | P2 — This month |
| 14 | 🟡 Medium | Pod Security | 12 containers with no `securityContext` defined | P2 — This month |
| 15 | 🟡 Medium | Pod Security | All containers lack `readOnlyRootFilesystem: true` | P2 — This month |
| 16 | 🟡 Medium | Secret Mgmt | 16 pods auto-mount SA tokens; many have no need for API access | P2 — This month |
| 17 | 🟡 Medium | Secret Mgmt | No ResourceQuotas on any namespace | P2 — This month |
| 18 | 🟡 Medium | Image Hygiene | 5 `game-2048` pods use `:latest` image tag | P2 — This month |
| 19 | 🟡 Medium | RBAC | Namespace roles with secrets access not reviewed post-install | P2 — This month |
| 20 | 🔵 Info | Secret Mgmt | No plaintext secrets detected in env vars | N/A — Compliant |
| 21 | 🔵 Info | CIS 1.2.6 | Authorization mode `Node,RBAC` — recommended | N/A — Compliant |
| 22 | 🔵 Info | CIS 1.2.22 | Insecure port disabled; TLS configured on API server | N/A — Compliant |

---

### Remediation Roadmap

#### 🔴 P0 — Immediate Actions (Day 1)

1. **Delete `minikube-rbac` ClusterRoleBinding**
   ```bash
   kubectl delete clusterrolebinding minikube-rbac
   ```

2. **Deploy Default-Deny NetworkPolicies** to all application namespaces:
   ```bash
   for ns in default game-2048 envoy-gateway-system kro-system; do
     kubectl apply -f - <<EOF
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: default-deny-all
     namespace: $ns
   spec:
     podSelector: {}
     policyTypes: [Ingress, Egress]
   EOF
   done
   ```
   > **Important:** Add targeted allow policies for each workload before deploying default-deny in production.

3. **Set `--anonymous-auth=false`** in `kube-apiserver` static pod manifest

4. **Configure API server audit logging** with an audit policy file

#### 🟠 P1 — This Week

5. Scope `kro-cluster-role` to minimum required permissions
6. Audit and prune `system:masters` / `kubeadm:cluster-admins` group membership
7. Apply PSA labels to all namespaces (`restricted` for workloads, `privileged` for `kube-system`)
8. Set `--profiling=false` on apiserver, controller-manager, and scheduler
9. Disable `automountServiceAccountToken` on `default` SAs and workload deployments
10. Remove `hostNetwork` and replace `/tmp` `hostPath` with `emptyDir` on `storage-provisioner`

#### 🟡 P2 — This Month

11. Add `securityContext` to all application containers (`backend`, `game-2048`, `kro`, `envoy-gateway`)
12. Set `readOnlyRootFilesystem: true` on all workload containers
13. Deploy `ResourceQuota` objects to all namespaces
14. Pin `game-2048` image to a specific digest
15. Review and remove `eg-gateway-helm-certgen` RoleBinding post-install
16. Evaluate adoption of an external secrets manager for secret rotation

---

## Appendix — Quick Remediation Snippets

### Secure `securityContext` Template
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  runAsGroup: 10001
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
  seccompProfile:
    type: RuntimeDefault
```

### Disable Service Account Token Auto-Mount (SA level)
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: <sa-name>
  namespace: <namespace>
automountServiceAccountToken: false
```

### Enable Pod Security Admission
```bash
kubectl label namespace default pod-security.kubernetes.io/enforce=restricted
kubectl label namespace default pod-security.kubernetes.io/warn=restricted
kubectl label namespace default pod-security.kubernetes.io/audit=restricted
kubectl label namespace kube-system pod-security.kubernetes.io/enforce=privileged
```

### Add ResourceQuota
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: default-quota
  namespace: default
spec:
  hard:
    pods: "20"
    requests.cpu: "2"
    requests.memory: 4Gi
    limits.cpu: "4"
    limits.memory: 8Gi
```

### API Server Hardening (add to `kube-apiserver.yaml`)
```yaml
- --anonymous-auth=false
- --profiling=false
- --audit-log-path=/var/log/kubernetes/audit.log
- --audit-log-maxage=30
- --audit-log-maxbackup=10
- --audit-log-maxsize=100
- --audit-policy-file=/etc/kubernetes/audit-policy.yaml
```

### Cluster Inventory at Time of Audit

| Resource | Count |
|----------|-------|
| Nodes | 1 (`minikube`) |
| Namespaces | 7 |
| Pods | 16 |
| ServiceAccounts | 50+ |
| ClusterRoles flagged | 13 |
| ClusterRoleBindings flagged | 3 |
| NetworkPolicies | **0** |
| ResourceQuotas | **0** |
| Containers without securityContext | 12 |
| Pods with auto-mounted SA tokens | 16 |

---

*Report generated by the `k8s_audit` skill on the Claude Agent SDK.*
*Cluster audited: `https://127.0.0.1:59325` · Audit date: 2026-02-23*
