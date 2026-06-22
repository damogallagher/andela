locals {
  name_prefix   = lower(replace("${var.project_name}-${var.environment}", "_", "-"))
  alb_name      = substr("${local.name_prefix}-alb", 0, 32)
  db_identifier = substr("${local.name_prefix}-postgres", 0, 63)

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Repository  = "damogallagher/andela"
  }
}
