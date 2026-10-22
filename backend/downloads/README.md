# 📥 Downloads Folder

Anything you place in this folder is automatically exposed to the frontend
under the **Downloads** page.

Suggested files to add:
- Sample MRI scans for testing (`.jpg`, `.png`)
- Patient report templates (`.pdf`)
- PINN model architecture docs
- Research papers you cite

Files are listed via `GET /api/downloads` and served via
`GET /api/downloads/{filename}`.
