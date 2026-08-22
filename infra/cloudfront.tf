resource "aws_cloudfront_origin_access_control" "web" {
  name                              = "${local.name}-web-oac"
  description                       = "OAC for TraceVault web origin (no public website endpoint)"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_cache_policy" "spa_query" {
  name        = "${local.name}-spa-query"
  comment     = "SPA cache including query strings (?trace_id=)"
  default_ttl = 60
  max_ttl     = 300
  min_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "none"
    }
    query_strings_config {
      query_string_behavior = "all"
    }
  }
}

resource "aws_cloudfront_response_headers_policy" "web" {
  name    = "${local.name}-web-headers"
  comment = "CSP, HSTS, nosniff for the TraceVault UI origin"

  security_headers_config {
    content_type_options {
      override = true
    }

    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      preload                    = true
      override                   = true
    }

    content_security_policy {
      override = true
      # connect-src uses execute-api wildcard to avoid a Terraform cycle
      # (API CORS origin = this distribution). Tighten after apply if needed.
      content_security_policy = join(" ", [
        "default-src 'self';",
        "connect-src 'self' https://*.execute-api.${var.aws_region}.amazonaws.com https://*.amazoncognito.com https://cognito-idp.${var.aws_region}.amazonaws.com;",
        "img-src 'self' data:;",
        "style-src 'self' 'unsafe-inline';",
        # 'unsafe-inline' is required by the Next.js static export, which emits
        # an inline bootstrap script. Reconciled from the live policy (#116).
        # It weakens the XSS defence CSP is here to provide — the fix is a
        # nonce/hash-based policy, tracked as a roadmap item, not a same-day
        # change during a delegated apply.
        "script-src 'self' 'unsafe-inline';",
        "frame-ancestors 'none';",
        "base-uri 'self';",
        "form-action 'self';",
      ])
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    referrer_policy {
      referrer_policy = "no-referrer"
      override        = true
    }

    # Present on the live policy; declared here so the config matches what is
    # deployed and a targeted plan is clean (#116). X-XSS-Protection is a
    # legacy header — the browser auditor it controls has been removed from
    # current browsers, so CSP above is the control that actually applies.
    # Dropping it is a separate call for the infra owner, not drift to fix.
    xss_protection {
      protection = true
      mode_block = true
      override   = true
    }
  }
}

resource "aws_cloudfront_distribution" "web" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "TraceVault web (Next export)"
  default_root_object = "index.html"
  http_version        = "http2and3"
  price_class         = "PriceClass_100"

  # WAFv2 attaches to CloudFront through this argument, not through
  # `aws_wafv2_web_acl_association` (which only supports REGIONAL resources).
  # Takes the ACL ARN for WAFv2; the ID form is WAF Classic. See #100.
  web_acl_id = aws_wafv2_web_acl.api.arn

  origin {
    domain_name              = aws_s3_bucket.web.bucket_regional_domain_name
    origin_id                = "web-s3"
    origin_access_control_id = aws_cloudfront_origin_access_control.web.id
  }

  default_cache_behavior {
    target_origin_id           = "web-s3"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = aws_cloudfront_cache_policy.spa_query.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.web.id
  }

  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1.2_2021"
  }
}
