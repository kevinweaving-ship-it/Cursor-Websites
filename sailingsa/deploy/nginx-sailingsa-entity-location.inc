# Include inside location ~ ^/sailor/ and location ~ ^/(boat|boat-name)/
# after proxy_pass + proxy_set_header lines.

limit_req zone=ssa_entity_ip burst=20 nodelay;
limit_req zone=ssa_entity_all burst=30 nodelay;
limit_conn ssa_entity_conn 4;

proxy_cache ssa_entity;
proxy_cache_methods GET HEAD;
proxy_cache_valid 200 5m;
proxy_cache_valid 301 10m;
proxy_cache_valid 404 2m;
proxy_cache_lock on;
proxy_cache_lock_timeout 5s;
proxy_ignore_headers Cache-Control Expires Set-Cookie;
add_header X-SSA-Cache $upstream_cache_status always;
