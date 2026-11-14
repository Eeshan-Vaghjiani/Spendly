# Accessibility

Spendly aims to make personal finance tracking and financial insights usable
by people with different abilities, devices, and access needs. This statement
covers the Android application and the browser-based administrator interface.

## Our approach

Accessibility improvements should support:

- Clear, readable text and layouts that accommodate larger text sizes.
- Meaningful labels for buttons, icons, form fields, and navigation.
- Sufficient contrast and information that does not rely on color alone.
- Practical touch targets and predictable navigation.
- Understandable validation messages, loading states, and error recovery.
- Screen-reader access and visible keyboard focus where applicable.

Accessibility is considered alongside usability, privacy, and financial clarity.

## Current status

Spendly is an academic/pilot project with ongoing accessibility work.
Small-screen layouts, text wrapping, and administrator-interface zoom and
focus behavior have received improvements and targeted checks.

Complete Android TalkBack coverage, spoken screen-reader announcements,
full keyboard-only administrator navigation, and physical-device coverage
have not been established. Spendly does not currently claim full WCAG
conformance or independent accessibility certification.

See the [acceptance status](docs/acceptance_status.md) for recorded evidence
and remaining limitations. Historical test results apply to the specific
versions and environments documented.

## Report an accessibility issue

Please use the
[bug report template](https://github.com/Eeshan-Vaghjiani/Spendly/issues/new?template=bug_report.md)
and include:

- The screen, control, or task affected.
- What you expected and what happened.
- Steps to reproduce the problem.
- Spendly version/build, if known.
- Device and Android version, or browser and operating system.
- Assistive technology and relevant settings, such as TalkBack, keyboard
  navigation, text size, or browser zoom.
- A suggested improvement, if you have one.

You do not need to disclose a disability or medical information.

Issues are public. Use synthetic examples and do not include private
financial records, SMS contents, account identifiers, passwords, or tokens.
Inspect screenshots and recordings before sharing them.

Sensitive security concerns should follow the [security policy](SECURITY.md).

## Contributing accessibility improvements

Follow [CONTRIBUTING.md](CONTRIBUTING.md) and keep changes focused on the
reported barrier.

For relevant changes:

- Preserve semantic labels, logical navigation, and visible focus.
- Check small-screen and enlarged-text layouts.
- Test with the relevant screen reader or keyboard workflow where available.
- Record the device, settings, results, and anything not tested.
- Use synthetic accounts and financial records.

Automated and widget tests support accessibility work but do not replace
testing with assistive technologies or feedback from users.
