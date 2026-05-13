CREATE TABLE user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_uid VARCHAR(64) NOT NULL,
  wechat_openid VARCHAR(128) NOT NULL,
  wechat_unionid VARCHAR(128) NULL,
  status TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_user_uid (user_uid),
  UNIQUE KEY uniq_wechat_openid (wechat_openid),
  KEY idx_user_created_at (created_at)
);

CREATE TABLE user_profile (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  nickname VARCHAR(64) NULL,
  avatar_url VARCHAR(255) NULL,
  gender TINYINT NULL,
  city VARCHAR(64) NULL,
  last_login_at DATETIME NULL,
  streak_days INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_profile_user_id (user_id),
  CONSTRAINT fk_user_profile_user FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE TABLE user_membership (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  membership_type VARCHAR(32) NOT NULL DEFAULT 'free',
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  started_at DATETIME NULL,
  expired_at DATETIME NULL,
  source VARCHAR(32) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_membership_user_id (user_id),
  KEY idx_membership_status (status),
  CONSTRAINT fk_membership_user FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE TABLE user_daily_quota (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  quota_date DATE NOT NULL,
  total_quota INT NOT NULL DEFAULT 3,
  used_quota INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_user_quota_date (user_id, quota_date),
  CONSTRAINT fk_daily_quota_user FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE TABLE content_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  content_uid VARCHAR(64) NOT NULL,
  content_type VARCHAR(32) NOT NULL,
  title VARCHAR(255) NOT NULL,
  body TEXT NULL,
  extra_json JSON NULL,
  content_source_type VARCHAR(32) NOT NULL DEFAULT 'preset',
  difficulty_level VARCHAR(32) NOT NULL DEFAULT 'beginner',
  source VARCHAR(64) NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'draft',
  created_by BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_content_uid (content_uid),
  KEY idx_content_type_status (content_type, status),
  KEY idx_content_source_type (content_source_type),
  KEY idx_content_difficulty (difficulty_level)
);

CREATE TABLE content_tag (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tag_name VARCHAR(64) NOT NULL,
  tag_type VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_tag_name_type (tag_name, tag_type)
);

CREATE TABLE content_tag_relation (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  content_id BIGINT NOT NULL,
  tag_id BIGINT NOT NULL,
  UNIQUE KEY uniq_content_tag (content_id, tag_id),
  CONSTRAINT fk_content_tag_relation_content FOREIGN KEY (content_id) REFERENCES content_item(id),
  CONSTRAINT fk_content_tag_relation_tag FOREIGN KEY (tag_id) REFERENCES content_tag(id)
);

CREATE TABLE content_generation_task (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  task_uid VARCHAR(64) NOT NULL,
  content_type VARCHAR(32) NOT NULL,
  generation_mode VARCHAR(32) NOT NULL DEFAULT 'batch',
  difficulty_level VARCHAR(32) NOT NULL DEFAULT 'beginner',
  domain_tag VARCHAR(64) NULL,
  prompt_text TEXT NULL,
  request_count INT NOT NULL,
  task_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  result_summary_json JSON NULL,
  created_by BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_generation_task_uid (task_uid),
  KEY idx_generation_task_status (task_status)
);

CREATE TABLE training_session (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_uid VARCHAR(64) NOT NULL,
  user_id BIGINT NOT NULL,
  mode VARCHAR(32) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'created',
  difficulty_level VARCHAR(32) NOT NULL DEFAULT 'beginner',
  source_entry VARCHAR(32) NULL,
  content_source_strategy VARCHAR(32) NOT NULL DEFAULT 'preset',
  started_at DATETIME NULL,
  submitted_at DATETIME NULL,
  ended_at DATETIME NULL,
  duration_seconds INT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_session_uid (session_uid),
  KEY idx_training_session_user_id (user_id),
  KEY idx_training_session_mode_status (mode, status),
  CONSTRAINT fk_training_session_user FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE TABLE training_session_content (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  content_id BIGINT NOT NULL,
  content_type VARCHAR(32) NOT NULL,
  role_in_session VARCHAR(32) NOT NULL,
  display_order INT NOT NULL DEFAULT 0,
  snapshot_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_session_content_session_id (session_id),
  CONSTRAINT fk_session_content_session FOREIGN KEY (session_id) REFERENCES training_session(id),
  CONSTRAINT fk_session_content_content FOREIGN KEY (content_id) REFERENCES content_item(id)
);

CREATE TABLE training_progress (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  current_stage VARCHAR(32) NOT NULL,
  progress_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_training_progress_session (session_id),
  CONSTRAINT fk_training_progress_session FOREIGN KEY (session_id) REFERENCES training_session(id)
);

CREATE TABLE training_submission (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  submission_uid VARCHAR(64) NOT NULL,
  session_id BIGINT NOT NULL,
  input_type VARCHAR(32) NOT NULL,
  raw_text TEXT NULL,
  transcribed_text TEXT NULL,
  input_duration_seconds INT NULL,
  audio_meta_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_submission_uid (submission_uid),
  KEY idx_training_submission_session_id (session_id),
  CONSTRAINT fk_training_submission_session FOREIGN KEY (session_id) REFERENCES training_session(id)
);

CREATE TABLE training_feedback (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  feedback_schema VARCHAR(64) NOT NULL,
  overall_score DECIMAL(4,1) NULL,
  summary TEXT NULL,
  strengths_json JSON NULL,
  weaknesses_json JSON NULL,
  suggestions_json JSON NULL,
  feedback_json JSON NOT NULL,
  generated_by VARCHAR(64) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_training_feedback_session (session_id),
  CONSTRAINT fk_training_feedback_session FOREIGN KEY (session_id) REFERENCES training_session(id)
);

CREATE TABLE card_round (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  round_no INT NOT NULL DEFAULT 1,
  total_cards INT NOT NULL DEFAULT 16,
  used_cards INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_card_round_session_id (session_id),
  CONSTRAINT fk_card_round_session FOREIGN KEY (session_id) REFERENCES training_session(id)
);

CREATE TABLE card_instance (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  round_id BIGINT NOT NULL,
  content_id BIGINT NOT NULL,
  card_status VARCHAR(32) NOT NULL DEFAULT 'hidden',
  position_index INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_card_round_position (round_id, position_index),
  KEY idx_card_instance_status (card_status),
  CONSTRAINT fk_card_instance_round FOREIGN KEY (round_id) REFERENCES card_round(id),
  CONSTRAINT fk_card_instance_content FOREIGN KEY (content_id) REFERENCES content_item(id)
);

CREATE TABLE speech_task (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  task_uid VARCHAR(64) NOT NULL,
  session_id BIGINT NULL,
  task_type VARCHAR(32) NOT NULL,
  task_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  provider VARCHAR(64) NULL,
  request_json JSON NULL,
  result_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_speech_task_uid (task_uid),
  KEY idx_speech_task_session_id (session_id),
  CONSTRAINT fk_speech_task_session FOREIGN KEY (session_id) REFERENCES training_session(id)
);

CREATE TABLE membership_order (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_no VARCHAR(64) NOT NULL,
  user_id BIGINT NOT NULL,
  product_type VARCHAR(32) NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  order_status VARCHAR(32) NOT NULL DEFAULT 'created',
  pay_channel VARCHAR(32) NOT NULL DEFAULT 'wechat_pay',
  paid_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_membership_order_no (order_no),
  KEY idx_membership_order_user_id (user_id),
  CONSTRAINT fk_membership_order_user FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE TABLE payment_transaction (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL,
  transaction_no VARCHAR(128) NOT NULL,
  channel_response_json JSON NULL,
  transaction_status VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_payment_transaction_no (transaction_no),
  CONSTRAINT fk_payment_transaction_order FOREIGN KEY (order_id) REFERENCES membership_order(id)
);

CREATE TABLE analytics_event (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  event_name VARCHAR(64) NOT NULL,
  user_id BIGINT NULL,
  session_id BIGINT NULL,
  mode VARCHAR(32) NULL,
  event_time DATETIME NOT NULL,
  event_date DATE NOT NULL,
  properties_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_analytics_event_name_date (event_name, event_date),
  KEY idx_analytics_event_user_id (user_id),
  KEY idx_analytics_event_session_id (session_id)
);

CREATE TABLE ai_prompt_template (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  prompt_key VARCHAR(64) NOT NULL,
  prompt_name VARCHAR(128) NOT NULL,
  business_domain VARCHAR(32) NOT NULL DEFAULT 'training_feedback',
  mode VARCHAR(32) NOT NULL DEFAULT 'card_association',
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  current_version_no INT NOT NULL DEFAULT 1,
  description TEXT NULL,
  created_by BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_ai_prompt_key (prompt_key),
  KEY idx_ai_prompt_domain_mode (business_domain, mode)
);

CREATE TABLE ai_prompt_version (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  template_id BIGINT NOT NULL,
  version_no INT NOT NULL,
  system_prompt TEXT NOT NULL,
  user_prompt_template TEXT NOT NULL,
  output_schema_json JSON NULL,
  model_name VARCHAR(64) NOT NULL,
  temperature DECIMAL(3,2) NOT NULL DEFAULT 0.70,
  max_output_tokens INT NOT NULL DEFAULT 1200,
  prompt_status VARCHAR(32) NOT NULL DEFAULT 'draft',
  change_note VARCHAR(255) NULL,
  created_by BIGINT NULL,
  published_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_prompt_template_version (template_id, version_no),
  KEY idx_ai_prompt_version_status (template_id, prompt_status),
  CONSTRAINT fk_ai_prompt_version_template FOREIGN KEY (template_id) REFERENCES ai_prompt_template(id)
);

CREATE TABLE ai_provider_config (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  provider_code VARCHAR(32) NOT NULL,
  provider_name VARCHAR(64) NOT NULL,
  api_base_url VARCHAR(255) NULL,
  model_name VARCHAR(64) NOT NULL,
  auth_mode VARCHAR(32) NOT NULL DEFAULT 'api_key',
  secret_ref VARCHAR(128) NOT NULL,
  timeout_ms INT NOT NULL DEFAULT 15000,
  is_default TINYINT NOT NULL DEFAULT 0,
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  extra_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_provider_code_model (provider_code, model_name)
);

CREATE TABLE ai_feedback_job (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  job_uid VARCHAR(64) NOT NULL,
  session_id BIGINT NOT NULL,
  submission_id BIGINT NOT NULL,
  prompt_template_id BIGINT NOT NULL,
  prompt_version_id BIGINT NOT NULL,
  provider_code VARCHAR(32) NOT NULL,
  model_name VARCHAR(64) NOT NULL,
  job_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  request_payload_json JSON NULL,
  response_payload_json JSON NULL,
  error_message VARCHAR(255) NULL,
  retried_count INT NOT NULL DEFAULT 0,
  started_at DATETIME NULL,
  finished_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_ai_feedback_job_uid (job_uid),
  KEY idx_ai_feedback_job_session (session_id),
  KEY idx_ai_feedback_job_status (job_status),
  CONSTRAINT fk_ai_feedback_job_session FOREIGN KEY (session_id) REFERENCES training_session(id),
  CONSTRAINT fk_ai_feedback_job_submission FOREIGN KEY (submission_id) REFERENCES training_submission(id),
  CONSTRAINT fk_ai_feedback_job_prompt_template FOREIGN KEY (prompt_template_id) REFERENCES ai_prompt_template(id),
  CONSTRAINT fk_ai_feedback_job_prompt_version FOREIGN KEY (prompt_version_id) REFERENCES ai_prompt_version(id)
);

CREATE TABLE ai_prompt_test_record (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  test_uid VARCHAR(64) NOT NULL,
  prompt_template_id BIGINT NOT NULL,
  prompt_version_id BIGINT NOT NULL,
  provider_code VARCHAR(32) NOT NULL,
  model_name VARCHAR(64) NOT NULL,
  input_payload_json JSON NOT NULL,
  output_payload_json JSON NULL,
  parsed_result_json JSON NULL,
  test_status VARCHAR(32) NOT NULL DEFAULT 'success',
  error_message VARCHAR(255) NULL,
  created_by BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_ai_prompt_test_uid (test_uid),
  KEY idx_ai_prompt_test_template_version (prompt_template_id, prompt_version_id),
  KEY idx_ai_prompt_test_created_at (created_at),
  CONSTRAINT fk_ai_prompt_test_template FOREIGN KEY (prompt_template_id) REFERENCES ai_prompt_template(id),
  CONSTRAINT fk_ai_prompt_test_version FOREIGN KEY (prompt_version_id) REFERENCES ai_prompt_version(id)
);

ALTER TABLE training_feedback
  ADD COLUMN prompt_template_id BIGINT NULL AFTER session_id,
  ADD COLUMN prompt_version_id BIGINT NULL AFTER prompt_template_id,
  ADD COLUMN provider_code VARCHAR(32) NULL AFTER feedback_json,
  ADD COLUMN model_name VARCHAR(64) NULL AFTER provider_code,
  ADD COLUMN response_meta_json JSON NULL AFTER model_name,
  ADD KEY idx_training_feedback_prompt_version (prompt_version_id),
  ADD CONSTRAINT fk_training_feedback_prompt_template FOREIGN KEY (prompt_template_id) REFERENCES ai_prompt_template(id),
  ADD CONSTRAINT fk_training_feedback_prompt_version FOREIGN KEY (prompt_version_id) REFERENCES ai_prompt_version(id);
