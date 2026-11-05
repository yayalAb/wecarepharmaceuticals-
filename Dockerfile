FROM odoo:18.0

# Install Ethiopic / Amharic fonts for wkhtmltopdf PDF generation
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-abyssinica-sil \
    fonts-noto-core \
    fonts-noto-extra \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

USER odoo
