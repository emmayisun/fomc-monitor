# Authentication & Paywall System

## Overview

This system implements user authentication and paywall content access control for Fed News Monitor.

## Features

### User Roles

1. **Free Users** (default)
   - Can view summaries and original article links
   - Cannot view full content of paywall articles
   - See "Member Only" badge on paywall articles

2. **Member Users** (registered/logged in)
   - Can view full content of all articles, including paywall articles
   - Access to content saved via browser scraper

### Authentication

- **Registration**: Users can register with email, name, and password
- **Login**: Existing members can log in to access member-only content
- **Session**: Authentication persists via localStorage (30-day expiration)

### Paywall Detection

Articles are automatically marked as paywall if:
- Source domain is in paywall list: `wsj.com`, `nytimes.com`, `ft.com`, `bloomberg.com`
- Content is very short (< 200 chars), indicating paywall blocking

### Browser Scraper Integration

The `browser_scraper.py` script allows you to:
1. Manually copy article content from your browser (when logged into paywall sites)
2. Save the content locally
3. Articles are automatically marked as paywall and saved with full content
4. Members can then view this saved content

## Usage

### For Users

1. **View as Free User**: Simply browse `news.html` - you'll see summaries and links
2. **Register**: Click "Login" → "Register" tab → Fill form → Access member content
3. **Login**: Click "Login" → Enter credentials → Access member content

### For Administrators

1. **Save Paywall Content**:
   ```bash
   # Copy article text from browser, save to file
   python browser_scraper.py <article_url> <text_file.txt>
   ```

2. **Articles are automatically**:
   - Marked with `has_paywall: true`
   - Saved with full content
   - Accessible only to members

## Technical Details

### Files

- `auth.js`: Client-side authentication manager
- `login.html`: Registration and login UI
- `news.html`: Updated with access control
- `news_scraper.py`: Paywall detection and HTML generation
- `browser_scraper.py`: Manual content saving with paywall marking

### Data Structure

Articles in `news.json` now include:
```json
{
  "has_paywall": true,
  "html_path": "data/news/article.html",
  ...
}
```

### Access Control Logic

- **Free users**: See summary + "View Original" link
- **Members**: See full content in HTML + "View Original" link
- **Article pages**: JavaScript checks auth status and shows/hides content

## Security Notes

⚠️ **Current Implementation**: Uses client-side authentication (localStorage)
- Suitable for demo/prototype
- **Not secure for production**

### For Production

Consider:
1. **Backend API**: Vercel serverless functions or separate backend
2. **JWT tokens**: Proper token-based authentication
3. **Database**: User storage (e.g., Supabase, Firebase)
4. **HTTPS**: Always use HTTPS in production
5. **Password hashing**: Never store plain passwords

## Future Enhancements

- [ ] Backend API for authentication
- [ ] Email verification
- [ ] Password reset
- [ ] Subscription management
- [ ] Payment integration
- [ ] Admin dashboard
