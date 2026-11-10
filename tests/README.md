# KATS Windows test launchers

All 16 test batch files live here to keep the repository root clean. Each
file invokes the shared `ops\tests.bat` dispatcher, which resolves the
correct repository path regardless of where CMD or PowerShell was started.

From the **repository root**, use:

```powershell
# PowerShell
.\tests\test-all.bat
.\tests\test-backend.bat
.\tests\test-frontend.bat
.\tests\test-api.bat
.\tests\test-security.bat
.\tests\test-database.bat
.\tests\test-e2e.bat
```

From CMD use the same paths without the leading `.`:

```cmd
tests\test-all.bat
tests\test-backend.bat
```

You can also change into this folder (`cd tests`) and run `.\test-all.bat`
in PowerShell or `test-all.bat` in CMD.

The root application command remains `.\start.bat`; all test scripts are
inside this folder, not the project root. The full suite requires Docker
Desktop and Python 3.12+/Node.js 22+. Staging-only load tests are opt-in
and excluded from test-all.

See [full testing guide](../docs/WINDOWS_TEST_LAUNCHERS.md) for all
16 categories, prerequisites, coverage, and safety constraints.

## Running test tasks from VS Code

Press **Ctrl+Shift+P → Tasks: Run Task** and choose a `KATS Test:` task.
Every test category now launches via `ops/vscode_task.ps1` using a VS Code
**process task** rather than a nested `cmd.exe /c` shell command. This
preserves folder paths containing spaces (for example,
`D:\\NEW PROJECTS\\Kats-Property-Management`) and returns the test's
real success/failure code. No separate terminal window is opened.
