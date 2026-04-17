# Static salesheet server for salesheet.goco.bz
FROM nginx:1.27-alpine

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static content — preserves /wpc-fence/ and future product paths
COPY wpc-fence /usr/share/nginx/html/wpc-fence

# Optional: a tiny landing/index at /
COPY index.html /usr/share/nginx/html/index.html

# Cloud Run listens on $PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
