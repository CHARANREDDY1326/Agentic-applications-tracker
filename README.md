📧 Gmail → 📒 Notion Automation using Agentic Approach

Automating Job Application Tracking with Python, Gmail API & Notion API






🌟 Overview

Tired of manually tracking job application emails? This project builds a serverless automation agent that:

Reads confirmation emails from Gmail 📧

Extracts job details (company, role, status) using Python + Gmail API

Updates your Notion Database 📒 automatically

Runs locally or inside GitHub Actions for cloud-native execution

This is a modern take on ETL pipelines for productivity:

Extract → Gmail API

Transform → Parse and clean email data

Load → Notion Database

🛠️ Tech Stack

Python 3.11 → Core logic

Google Gmail API → Secure email access (OAuth2)

Notion API → Update job application database

GitHub Actions → CI/CD & automation on cloud runners

dotenv / GitHub Secrets → Secure credentials handling

🚀 Features

✅ Automatically sync Gmail → Notion
✅ Cloud-ready (runs in GitHub Actions)
✅ Local development friendly
✅ Modular & extensible — add more integrations (Slack, Sheets, etc.)
