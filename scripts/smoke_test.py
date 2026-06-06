#!/usr/bin/env python3
"""Run a minimal external smoke test against a deployed JobHunter Pro API."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import urllib.error
import urllib.parse
import urllib.request


class SmokeFailure(RuntimeError):
    pass


def _request(opener: urllib.request.OpenerDirector, base_url: str, path: str, method: str = "GET", body: dict | None = None) -> dict:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(request, timeout=20) as response:
            payload = response.read().decode("utf-8")
            return {
                "status": response.status,
                "json": json.loads(payload) if payload else {},
            }
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        parsed = json.loads(payload) if payload else {}
        return {"status": error.code, "json": parsed}


def run_smoke_test(base_url: str, username: str | None, password: str | None) -> list[str]:
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    checks: list[str] = []

    health = _request(opener, base_url, "/api/health")
    if health["status"] != 200 or health["json"].get("status") != "ok":
        raise SmokeFailure(f"/api/health failed: {health}")
    checks.append("health")

    auth_config = _request(opener, base_url, "/api/auth/config")
    if auth_config["status"] != 200:
        raise SmokeFailure(f"/api/auth/config failed: {auth_config}")
    checks.append("auth-config")

    if auth_config["json"].get("auth_enabled"):
        if not username or not password:
            raise SmokeFailure("Auth is enabled; provide --username/--password or AUTH_USERNAME/AUTH_PASSWORD.")
        login = _request(opener, base_url, "/api/auth/login", method="POST", body={"username": username, "password": password})
        if login["status"] != 200:
            raise SmokeFailure(f"/api/auth/login failed: {login}")
        checks.append("login")

    ready = _request(opener, base_url, "/api/ready")
    if ready["status"] != 200 or ready["json"].get("status") != "ready":
        raise SmokeFailure(f"/api/ready failed: {ready}")
    checks.append("ready")

    dashboard = _request(opener, base_url, "/api/dashboard")
    if dashboard["status"] != 200:
        raise SmokeFailure(f"/api/dashboard failed: {dashboard}")
    checks.append("dashboard")

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test a deployed JobHunter Pro instance.")
    parser.add_argument("--base-url", default=os.getenv("JOBHUNTER_BASE_URL"), help="Base URL, e.g. https://app.example.com")
    parser.add_argument("--username", default=os.getenv("AUTH_USERNAME"))
    parser.add_argument("--password", default=os.getenv("AUTH_PASSWORD"))
    args = parser.parse_args()

    if not args.base_url:
        print("Missing --base-url or JOBHUNTER_BASE_URL.")
        return 2

    try:
        checks = run_smoke_test(args.base_url, args.username, args.password)
    except SmokeFailure as error:
        print(f"Smoke test failed: {error}")
        return 1

    print("Smoke test passed:", ", ".join(checks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
