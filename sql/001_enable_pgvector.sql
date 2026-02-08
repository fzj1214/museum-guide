-- ============================================
-- Museum Guide MVP - Database Schema Setup
-- ============================================
-- Run this script in Supabase SQL Editor to set up the database schema.
-- Execute scripts in order: 001, 002, 003

-- ============================================
-- 001: Enable pgvector extension
-- ============================================

-- Enable the pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;
