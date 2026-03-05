# PowerShell script to start TikTok Bot Dashboard
Write-Host "========================================"
Write-Host "Starting TikTok Bot Dashboard"
Write-Host "========================================"

# Start the Django server in the background
Write-Host "Starting Django development server..."

# Start the server in a new PowerShell window
Start-Process powershell -ArgumentList "-Command", "python manage.py runserver" -WindowStyle Normal

# Wait for server to start
Write-Host "Waiting for server to start..."
Start-Sleep -Seconds 5

# Open the web browser to the dashboard
Write-Host "Opening dashboard in your web browser..."
Start-Process "http://localhost:8000"

Write-Host ""
Write-Host "Server started! Opening http://localhost:8000 in your browser..."
Write-Host ""
Write-Host "To stop the server, close the terminal window or press Ctrl+C"
Write-Host "Username: admin"
Write-Host "Password: password"
Write-Host ""

Write-Host "Press any key to exit..."
$host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")