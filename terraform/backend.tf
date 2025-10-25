terraform {
  backend "s3" {
    bucket         = "codehealer-terraform-state"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "codehealer-terraform-locks"
  }
}