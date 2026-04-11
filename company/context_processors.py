def company_shell(request):
    user = getattr(request, "user", None)
    is_company = bool(getattr(user, "is_authenticated", False) and getattr(user, "role", None) == "company")
    return {
        "company_nav": {
            "is_company": is_company,
            "base_url": "/company/",
            "links": [
                {"label": "Overview", "url": "/company/"},
                {"label": "Internships", "url": "/company/internships/"},
                {"label": "Applicants", "url": "/company/applicants/"},
                {"label": "Interviews", "url": "/company/interviews/"},
                {"label": "Settings", "url": "/company/settings/"},
            ],
        }
    }
