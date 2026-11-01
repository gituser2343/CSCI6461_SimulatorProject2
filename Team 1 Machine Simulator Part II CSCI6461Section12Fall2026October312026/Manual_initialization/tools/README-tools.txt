browser_test.js.txt is browser_test.js, renamed because Gmail refuses to
deliver .js attachments even inside a zip. Rename it back to browser_test.js
before running it.

    python3 test_program1.py     reference suite: 8 cases + 300 random trials
    node browser_test.js         drives the real simulator via Playwright
