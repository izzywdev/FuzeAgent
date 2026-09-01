#!/usr/bin/env python3
"""Assert properties of a rendered Helm chart that a lint cannot see.

  1. Every Service selects EXACTLY ONE workload. A selector that matches two
     Deployments silently round-robins API traffic into the wrong container
     (e.g. into nginx and back); a selector that matches zero is a Service with
     no endpoints, which looks fine until a call times out.
  2. No container image resolves to an empty repository or tag.
  3. Every probe targets a port the container actually declares.
"""
import sys, yaml

def labels_match(selector, labels):
    return all(labels.get(k) == v for k, v in (selector or {}).items())

def main(path):
    docs = [d for d in yaml.safe_load_all(open(path)) if d]
    workloads = []   # (kind, name, podLabels)
    services = []
    problems = []
    for d in docs:
        k = d.get('kind')
        if k in ('Deployment', 'StatefulSet', 'DaemonSet'):
            workloads.append((k, d['metadata']['name'],
                              (d['spec']['template']['metadata'].get('labels') or {}),
                              d))
        elif k == 'Service':
            services.append(d)

    for svc in services:
        sel = svc['spec'].get('selector')
        name = svc['metadata']['name']
        if not sel:
            problems.append(f"Service {name}: no selector at all")
            continue
        hits = [w[1] for w in workloads if labels_match(sel, w[2])]
        if len(hits) != 1:
            problems.append(
                f"Service {name}: selector {sel} matches {len(hits)} workloads {hits} (expected exactly 1)")
        else:
            print(f"  OK  Service {name:34} -> {hits[0]}")

    for kind, name, _lab, d in workloads:
        for c in d['spec']['template']['spec'].get('containers', []):
            img = c.get('image', '')
            if not img or img.endswith(':') or img.startswith(':'):
                problems.append(f"{kind} {name}/{c['name']}: bad image {img!r}")
            declared = {p.get('name') for p in (c.get('ports') or [])} | {
                p.get('containerPort') for p in (c.get('ports') or [])}
            for probe in ('readinessProbe', 'livenessProbe', 'startupProbe'):
                hp = (c.get(probe) or {}).get('httpGet')
                if hp and hp.get('port') not in declared:
                    problems.append(
                        f"{kind} {name}/{c['name']}: {probe} targets port {hp.get('port')!r}, "
                        f"container declares {sorted(x for x in declared if x is not None)}")

    print(f"  {len(workloads)} workload(s), {len(services)} service(s)")
    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print("  ✗", p)
        return 1
    print("  all assertions passed")
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
