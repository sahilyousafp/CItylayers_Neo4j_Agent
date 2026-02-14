# Security Guidelines

## API Key Management

### 🔐 Environment Variables
All sensitive credentials are stored in environment variables and loaded via `.env` file.

**NEVER commit the `.env` file to version control.**

### Setup Instructions

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Fill in your actual credentials in `.env`:**
   - `NEO4J_URI`: Your Neo4j database URI
   - `NEO4J_USERNAME`: Your Neo4j username
   - `NEO4J_PASSWORD`: Your Neo4j password
   - `GOOGLE_API_KEY`: Your Google Gemini API key (if using Google LLM)
   - `FLASK_SECRET_KEY`: A secure random string for Flask sessions
   - `MAPBOX_ACCESS_TOKEN`: Your Mapbox API token

3. **Generate secure keys:**
   ```python
   # For FLASK_SECRET_KEY
   import secrets
   print(secrets.token_hex(32))
   ```

### Protected Files

The following files contain sensitive information and are protected by `.gitignore`:
- `.env` - Contains all API keys and credentials
- `.env.local` - Local overrides
- `.env.*.local` - Environment-specific local overrides

### Security Checklist

- ✅ `.env` file is in `.gitignore`
- ✅ No hardcoded credentials in source code
- ✅ `.env.example` provided as template (without real credentials)
- ✅ Config validation ensures required credentials are present
- ✅ All API keys loaded from environment variables

### Best Practices

1. **Rotate credentials regularly** - Update API keys and passwords periodically
2. **Use different credentials per environment** - Dev, staging, and production should have separate credentials
3. **Limit API key permissions** - Use least-privilege principle
4. **Monitor API usage** - Watch for unusual activity
5. **Never share `.env` files** - Use secure channels for credential sharing

### Emergency Response

If credentials are accidentally committed:
1. **Immediately rotate all exposed credentials**
2. **Remove from git history:** Use `git filter-branch` or BFG Repo-Cleaner
3. **Force push cleaned history** (coordinate with team)
4. **Audit logs** for unauthorized access

### Supported Credential Sources

- `.env` file (development)
- System environment variables (production)
- Container secrets (Docker/Kubernetes)
- Cloud provider secret managers (AWS Secrets Manager, Azure Key Vault, etc.)
