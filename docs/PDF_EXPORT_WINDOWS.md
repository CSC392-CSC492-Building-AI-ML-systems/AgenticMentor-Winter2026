# PDF Export on Windows (WeasyPrint / GTK)

The exporter uses **WeasyPrint** to generate PDFs. On Windows, WeasyPrint needs **Pango/GTK** DLLs. If you see:

- `WeasyPrint (GTK) not found. PDF export disabled; falling back to HTML.`
- or `WeasyPrint could not import some external libraries`

then PDF generation is disabled and the app saves **HTML** instead. You can still get a PDF by opening the `.html` file in a browser and using **Print → Save as PDF**.

To enable **native PDF export** on Windows, use one of the options below.

---

## Option 1: MSYS2 + Pango (recommended)

1. **Install [MSYS2](https://www.msys2.org/)** (default options).
2. Open **MSYS2** (the MSYS2 UCRT64 or MSYS2 MSYS shell).
3. Install Pango and dependencies:
   ```bash
   pacman -S mingw-w64-ucrt-x86_64-pango
   ```
   (If that fails, try: `pacman -S mingw-w64-x86_64-pango`)
4. Close MSYS2.
5. **Tell Python where the DLLs are** (required when running from normal Windows terminal):
   - **Temporary (current session):** in PowerShell:
     ```powershell
     $env:WEASYPRINT_DLL_DIRECTORIES = "C:\msys64\ucrt64\bin"
     ```
     If you used `mingw64` instead of `ucrt64`, use:
     ```powershell
     $env:WEASYPRINT_DLL_DIRECTORIES = "C:\msys64\mingw64\bin"
     ```
   - **Permanent:** add a **System** or **User** environment variable:
     - Name: `WEASYPRINT_DLL_DIRECTORIES`
     - Value: `C:\msys64\ucrt64\bin` (or `C:\msys64\mingw64\bin`)
6. **Avoid Fontconfig errors/crashes when generating PDF:** set the font config path (same session or permanent):
   ```powershell
   $env:FONTCONFIG_FILE = "C:\msys64\ucrt64\etc\fonts\fonts.conf"
   ```
   (Use `mingw64` instead of `ucrt64` if you installed that variant.)
7. **Start Python only after** setting the variable(s) above (env vars are read when WeasyPrint is first imported). Then run:
   ```powershell
   python -m weasyprint --info
   ```
   If that runs without errors, PDF export in the app should work. Run your app or tests from the same shell so they see the same env.

---

## Option 2: WSL (Windows Subsystem for Linux)

Install [WSL](https://docs.microsoft.com/en-us/windows/wsl/), then inside the Linux environment install WeasyPrint as on Linux (e.g. `apt install weasyprint` or `pip install weasyprint` with system Pango). Run the app from WSL if you want PDFs generated there.

---

## Option 3: Use the HTML fallback

No extra setup: the exporter saves an `.html` file. Open it in Chrome or Edge and use **Print → Save as PDF** to get a PDF.

---

## References

- [WeasyPrint first steps (installation)](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation)
- [WeasyPrint troubleshooting](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#troubleshooting) (e.g. `WEASYPRINT_DLL_DIRECTORIES`)
