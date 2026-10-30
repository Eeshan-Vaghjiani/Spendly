"""Process-death/reopen checks for the disposable SMS lifecycle harness only."""
import json
import time
import urllib.request

from run_mpesa_sms_lab import BASE, PACKAGE, adb, request, sms, assert_disposable_emulator


def main():
    assert_disposable_emulator()
    target = request("/sms-acceptance-target")
    if target.get("disposable") is not True or target.get("database") != "in_memory" or request("/sms-lab-checkpoint")["phase"] != "complete":
        raise RuntimeError("Complete the guarded in-memory acceptance harness first")
    login = request("/auth/login", {"email": "sms-native-alpha@example.invalid", "password": "SyntheticNativeOnly123!"})
    token = login["access_token"]  # Synthetic fixture only; never output or persist.
    try:
        run_checks(token)
    finally:
        # This cleanup also runs after a failed assertion. Never leave a capable
        # test binding running or an encrypted fixture JWT behind in the app.
        try:
            req = urllib.request.Request(BASE + "/mpesa/settings", method="PUT", data=b'{"enabled":false}',
                headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as response:
                if json.load(response)["data"]["enabled"] is not False:
                    raise RuntimeError("Could not withdraw synthetic service consent")
        finally:
            adb("shell", "am", "force-stop", PACKAGE)
            adb("uninstall", PACKAGE)


def run_checks(token):

    def financial_rows():
        req = urllib.request.Request(BASE + "/transactions?per_page=100", headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.load(response)["data"]["total"]

    def wait_rows(count):
        for _ in range(100):
            if financial_rows() == count:
                return
            time.sleep(1)
        raise RuntimeError(f"Expected {count} synthetic financial rows")

    def reopen():
        adb("shell", "am", "start", "-n", PACKAGE + "/com.evagh.capstone.spending_support.MainActivity")
        time.sleep(8)

    wait_rows(6)
    reopen()
    before = adb("shell", "pidof", PACKAGE, check=False).strip()
    if not before:
        raise RuntimeError("Lifecycle harness did not open the real application")
    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    for _ in range(20):
        adb("shell", "am", "kill", PACKAGE)
        time.sleep(1)
        if not adb("shell", "pidof", PACKAGE, check=False).strip():
            break
    else:
        raise RuntimeError("Package did not become a killed background process")
    sms(9)
    wait_rows(7)
    after = adb("shell", "pidof", PACKAGE, check=False).strip()
    if not after or after == before:
        raise RuntimeError("Expected a new native process after SMS delivery")
    print("SMS_LIFECYCLE:process_death_and_encrypted_binding_restore:passed", flush=True)

    adb("shell", "am", "force-stop", PACKAGE)
    sms(10)
    time.sleep(8)
    if financial_rows() != 7:
        raise RuntimeError("Force-stopped application unexpectedly imported SMS")
    reopen()
    wait_rows(8)
    print("SMS_LIFECYCLE:force_stop_pause_and_real_app_reopen_catchup:passed", flush=True)

    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    adb("shell", "pm", "revoke", PACKAGE, "android.permission.READ_SMS")
    if "android.permission.READ_SMS: granted=false" not in adb("shell", "dumpsys", "package", PACKAGE):
        raise RuntimeError("Test permission revocation was not applied")
    sms(11)
    time.sleep(8)
    if financial_rows() != 8:
        raise RuntimeError("Revoked SMS permission unexpectedly allowed import")
    print("SMS_LIFECYCLE:permission_revocation:passed", flush=True)


if __name__ == "__main__":
    main()
