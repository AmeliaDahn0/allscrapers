# GitHub Actions Setup

This repository includes an automated GitHub Actions workflow to run the Membean scraper every 2 hours on a schedule.

## 🔧 Setup Instructions

### 1. Configure Repository Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `MEMBEAN_USERNAME` | Your Membean login username | `your_username` |
| `MEMBEAN_PASSWORD` | Your Membean login password | `your_password` |
| `SUPABASE_URL` | Your Supabase project URL | `https://xyz.supabase.co` |
| `SUPABASE_KEY` | Your Supabase anon key | `eyJhbGci...` |

### 2. Enable GitHub Actions

1. Go to your repository → Actions tab
2. If prompted, click "I understand my workflows, go ahead and enable them"

### 3. Available Workflows

#### Membean Scraper (`membean-scraper.yml`)
- **Schedule**: Every 2 hours (at minute 0 of every 2nd hour)
- **Function**: Runs `membean_scraper.py` to collect current data
- **Output**: Updates data files and commits to repository

### 4. Manual Triggering

The workflow can be manually triggered:
1. Go to Actions tab in your repository
2. Select the "Membean Scraper" workflow
3. Click "Run workflow" button

### 5. Monitor Workflow Runs

- Check the Actions tab to see workflow execution status
- View logs to troubleshoot any issues
- Failed runs will send email notifications (if enabled)

## 🔒 Security Notes

- Repository secrets are encrypted and only accessible to GitHub Actions
- Never commit credentials to your repository
- The workflow uses headless browser mode for automation
- All data is stored in your Supabase database and repository

## ⚠️ Important Considerations

1. **Rate Limiting**: Be mindful of Membean's terms of service
2. **Browser Resources**: GitHub Actions provides limited compute time
3. **Network Stability**: The workflow may occasionally fail due to network issues
4. **Data Storage**: Committed data files will count toward repository size
5. **Frequency**: Running every 2 hours will create more frequent data snapshots

## 🛠 Troubleshooting

### Common Issues:

1. **Login Failures**: Check that credentials in secrets are correct
2. **Browser Timeout**: Playwright may timeout on slow networks
3. **Supabase Errors**: Verify database connection and permissions
4. **Git Push Failures**: Ensure repository permissions allow Actions to push

### Debugging Steps:

1. Check workflow logs in Actions tab
2. Test secrets by running the workflow manually
3. Verify Membean website accessibility
4. Check Supabase database status

## 📊 Monitoring Data Collection

The workflow will automatically:
- Collect student progress data every 2 hours
- Save to JSON files in `/data` directory  
- Upload to Supabase database
- Commit changes back to repository
- Provide timestamped logs for tracking 