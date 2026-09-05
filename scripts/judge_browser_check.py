#!/usr/bin/env python3
"""Browser verification for the judge-facing MandateGuard flow.

This is a standalone acceptance script rather than a pytest test so the historical
unit-test count remains meaningful. It expects both the Python-backed workspace
and a static public/ server to be running.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright


ARTIFACT_DIR = Path("browser-artifacts")


def assert_no_horizontal_overflow(page: Page) -> None:
    overflow = page.evaluate(
        """() => ({
          viewport: window.innerWidth,
          html: document.documentElement.scrollWidth,
          body: document.body.scrollWidth
        })"""
    )
    assert overflow["html"] <= overflow["viewport"] + 2, overflow
    assert overflow["body"] <= overflow["viewport"] + 2, overflow


def collect_browser_errors(page: Page) -> list[str]:
    errors: list[str] = []
    page.on("console", lambda message: errors.append(f"console: {message.text}") if message.type == "error" else None)
    page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
    return errors


def verify_primary_flow(page: Page, base_url: str) -> None:
    errors = collect_browser_errors(page)
    page.goto(base_url, wait_until="networkidle")
    expect(page).to_have_title("MandateGuard · Scheduled UPI AutoPay recovery")
    expect(page.locator("#mode")).to_have_text("Python engine connected")
    expect(page.get_by_role("heading", level=1)).to_contain_text("Recover failed scheduled UPI AutoPay payments")
    expect(page.locator(".hero-lead")).to_contain_text("explicit controls for when to retry")

    page.screenshot(path=str(ARTIFACT_DIR / "desktop-before-run.png"), full_page=True)

    page.get_by_role("button", name="Run recovery demonstration").click()
    expect(page.locator("#run-state")).to_contain_text("Demonstration executed.", timeout=45_000)

    recover = page.locator("#case-recover")
    revoked = page.locator("#case-revoked")
    timeout = page.locator("#case-timeout")
    expect(recover).to_contain_text("Retry is permitted")
    expect(recover).to_contain_text("Recovered")
    expect(recover).to_contain_text("PROVIDER CALLS")
    expect(recover).to_contain_text("1")
    expect(revoked).to_contain_text("Stop before the provider")
    expect(revoked).to_contain_text("Stopped")
    expect(revoked).to_contain_text("0")
    expect(timeout).to_contain_text("Ask a human before another action")
    expect(timeout).to_contain_text("Human review")
    expect(timeout).to_contain_text("1")
    expect(timeout).to_contain_text("Postcondition unknown")

    # Every case must be accounted for, including calls without a confirmed result.
    expect(page.locator("#stats .stat-card")).to_have_count(6)
    expect(page.locator("#stats")).to_contain_text("Awaiting outcome")
    expect(page.locator("#interpreter-comparison tr")).to_have_count(3)
    expect(page.locator(".ai-card")).to_contain_text("offline interpreter stub")

    # A late response must stay attached to the case that requested it.
    page.locator(".boundary-panel > summary").click()
    pending = []
    page.route("**/api/demo/scenario", lambda route: pending.append(route))
    page.locator("#run-boundary").click()
    page.wait_for_function("document.querySelector('#run-boundary').disabled")
    page.locator('[data-boundary="notice"]').click()
    recorded = json.loads(Path("public/evidence.json").read_text(encoding="utf-8"))
    assert len(pending) == 1
    pending[0].fulfill(json=recorded["scenarios"]["ambiguous"])
    expect(page.locator("#run-boundary")).to_be_enabled()
    expect(page.locator("#boundary-title")).to_have_text(recorded["scenarios"]["notice"]["title"])
    page.locator('[data-boundary="ambiguous"]').click()
    expect(page.locator("#boundary-title")).to_have_text(recorded["scenarios"]["ambiguous"]["title"])
    expect(page.locator("#boundary-mode")).to_contain_text("JUST EXECUTED")
    page.unroute("**/api/demo/scenario")
    page.locator(".boundary-panel > summary").click()

    recover.get_by_role("button", name="View decision receipt").click()
    expect(page.locator("#receipt-dialog")).to_be_visible()
    page.get_by_role("button", name="Verify audit chain + tamper check").click()
    expect(page.locator("#verify-result")).to_contain_text("Verified in this browser", timeout=10_000)
    expect(page.locator("#verify-result")).to_contain_text("editing the first decision breaks the chain")

    with page.expect_download() as download_info:
        page.get_by_role("button", name="Download receipt").click()
    receipt_download = download_info.value
    receipt_path = ARTIFACT_DIR / receipt_download.suggested_filename
    receipt_download.save_as(receipt_path)
    assert receipt_path.stat().st_size > 500
    page.get_by_role("button", name="Close receipt").click()

    with page.expect_download() as download_info:
        page.locator("#export-batch").click()
    batch_download = download_info.value
    batch_path = ARTIFACT_DIR / batch_download.suggested_filename
    batch_download.save_as(batch_path)
    assert batch_path.stat().st_size > 100_000

    page.locator("#evaluation > details > summary").click()
    expect(page.locator("#policy-table tr")).to_have_count(9)
    expect(page.locator("#price-curve .price-point")).to_have_count(9)

    # Error handling: return malformed JSON. Existing evidence must remain visible,
    # without manufacturing a browser-level network error in the acceptance log.
    page.route(
        "**/api/demo/batch",
        lambda route: route.fulfill(status=200, content_type="application/json", body="{not-json"),
    )
    page.get_by_role("button", name="Run recovery demonstration").click()
    expect(page.locator("#run-state")).to_contain_text("Demonstration could not be refreshed.", timeout=15_000)
    expect(recover).to_contain_text("Recovered")
    page.unroute("**/api/demo/batch")

    # Basic keyboard path: the first Tab target from a fresh load is the skip link.
    page.goto(base_url, wait_until="networkidle")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement && document.activeElement.classList.contains('skip')")

    assert_no_horizontal_overflow(page)
    page.screenshot(path=str(ARTIFACT_DIR / "desktop-verified.png"), full_page=True)
    assert not errors, "Browser errors:\n" + "\n".join(errors)


def verify_mobile(page: Page, base_url: str) -> None:
    errors = collect_browser_errors(page)
    page.goto(base_url, wait_until="networkidle")
    expect(page.locator("#mode")).to_have_text("Python engine connected")
    assert_no_horizontal_overflow(page)

    page.get_by_role("button", name="Run recovery demonstration").click()
    expect(page.locator("#run-state")).to_contain_text("Demonstration executed.", timeout=45_000)
    expect(page.locator("#case-recover")).to_contain_text("Retry is permitted")
    expect(page.locator("#case-revoked")).to_contain_text("Stop before the provider")
    expect(page.locator("#case-timeout")).to_contain_text("Ask a human before another action")
    assert_no_horizontal_overflow(page)
    page.screenshot(path=str(ARTIFACT_DIR / "mobile-390-verified.png"), full_page=True)
    assert not errors, "Mobile browser errors:\n" + "\n".join(errors)


def verify_static_truthfulness(page: Page, static_url: str) -> None:
    errors = collect_browser_errors(page)
    page.goto(static_url, wait_until="networkidle")
    expect(page.locator("#mode")).to_have_text("Recorded engine evidence")
    page.get_by_role("button", name="Replay recovery demonstration").click()
    expect(page.locator("#run-state")).to_contain_text("Recorded evidence replayed.")
    expect(page.locator("#run-state")).to_contain_text("Static hosting does not execute Python")
    expect(page.locator("#case-revoked")).to_contain_text("0")
    assert_no_horizontal_overflow(page)
    assert not errors, "Static browser errors:\n" + "\n".join(errors)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--static-url", default="http://127.0.0.1:8090")
    args = parser.parse_args()

    ARTIFACT_DIR.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        desktop = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        verify_primary_flow(desktop.new_page(), args.base_url)
        desktop.close()

        mobile = browser.new_context(viewport={"width": 390, "height": 844}, accept_downloads=True)
        verify_mobile(mobile.new_page(), args.base_url)
        mobile.close()

        static = browser.new_context(viewport={"width": 1280, "height": 900})
        verify_static_truthfulness(static.new_page(), args.static_url)
        static.close()
        browser.close()

    print("judge browser verification passed")
    print("desktop: live Python batch + three cases + receipt/tamper + exports + evaluation + error state")
    print("mobile: 390px live flow + overflow check")
    print("static: recorded-evidence labeling verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
