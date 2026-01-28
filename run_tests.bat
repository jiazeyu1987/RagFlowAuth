@echo off
cd /d D:\ProjectPackage\RagflowAuth\backend
python -m unittest tests.test_password_change_api -v
