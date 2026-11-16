"""Tests that fail on purpose because of an intentional Altru change.

Upstream test files are never edited (that would conflict on every upstream
merge). Instead each test listed here is marked as a strict expected failure:

- if it fails, the run stays green (the Altru change is still in place);
- if it starts passing, the run fails (XPASS strict), meaning upstream or our
  code changed and the entry should be removed or the change re-checked.

Only add a test after confirming the failure is an intended Altru difference,
not a bug. See docs/ALTUR.md "Upstream updates".
"""
import sys

import pytest


DIVERGENCES = {
    'brand': (
        'Upstream text names Hermes, its CLI commands or upstream links; Altru shows its own name, the local setup guide or bundled help.',
        [
            'test_1695_aiagent_import_error_detail.py::TestAIAgentImportErrorDetail::test_handles_no_relevant_sys_path_entries',
            'test_1695_aiagent_import_error_detail.py::TestAIAgentImportErrorDetail::test_includes_pip_install_editable_hint',
            'test_1695_aiagent_import_error_detail.py::TestAIAgentImportErrorDetail::test_preserves_original_message_for_log_scrapers',
            'test_4109_notification_focus_existing_tab.py::test_service_worker_update_delivery_keeps_versioned_no_store_route',
            'test_4109_notification_focus_existing_tab.py::test_test_notification_without_sid_still_targets_current_page_for_reuse',
            'test_a11y_transcript_landmarks.py::test_latest_assistant_landmark_helper_is_named_but_not_focusable',
            'test_batch_fixes.py::TestSystemTheme::test_i18n_cmd_theme_all_locales',
            'test_batch_fixes.py::TestSystemTheme::test_i18n_cmd_theme_includes_system_english',
            'test_chinese_locale.py::test_chinese_locale_includes_representative_translations',
            'test_cli_only_slash_commands.py::test_browser_cli_only_response_explains_server_side_browser_tools',
            'test_cli_only_slash_commands.py::test_cli_only_response_helper_uses_canonical_command_name',
            'test_cli_only_slash_commands.py::test_cli_only_response_mentions_webui_scope',
            'test_commands_endpoint.py::test_credits_command_returns_not_logged_in_message',
            'test_ctl_script.py::test_start_refuses_second_instance_when_launchd_job_owns_the_port',
            'test_custom_providers_in_panel.py::TestCustomProvidersInGetProviders::test_providers_panel_renders_config_yaml_custom_providers',
            'test_czech_locale.py::test_czech_locale_includes_representative_translations',
            'test_gateway_lifecycle_controls.py::test_gateway_lifecycle_missing_cli_returns_sanitized_error',
            'test_home_route_html_error.py::test_home_route_internal_error_returns_html_503_not_json',
            'test_issue1116_composer_placeholder.py::TestComposerPlaceholderProfile::test_applyBotName_falls_back_to_bot_name',
            'test_issue1361_cancel_data_loss.py::test_cancel_copy_falls_back_to_hermes_for_blank_bot_name',
            'test_issue1362_codex_oauth_onboarding.py::test_codex_protocol_requests_send_explicit_user_agent[False]',
            'test_issue1362_codex_oauth_onboarding.py::test_codex_protocol_requests_send_explicit_user_agent[True]',
            'test_issue1362_codex_oauth_onboarding.py::test_unsupported_note_mentions_codex_and_claude_as_in_app',
            'test_issue1560_password_env_var_lock.py::test_i18n_locked_string_mentions_env_var_name_in_all_locales',
            'test_issue2453_agent_source_boundary.py::test_docker_startup_warns_when_agent_source_mount_is_writable',
            'test_issue2462_theme_i18n.py::test_theme_command_help_mentions_current_theme_and_skin_values',
            'test_issue2785_gateway_cron_guidance.py::test_cron_panel_loads_gateway_status_for_scheduling_guidance',
            'test_issue3227_help_tab.py::test_help_pane_present',
            'test_issue4300_gateway_approval_notice.py::test_gateway_chat_event_payload_contains_type_and_message',
            'test_issue4843_pet_webui_command.py::test_pet_slash_intercept_bypasses_generic_agent_execution',
            'test_issue5139_gateway_approval_offline_notice.py::test_gateway_chat_emits_offline_warning_for_unreachable_probe',
            'test_issue5139_gateway_approval_offline_notice.py::test_gateway_chat_keeps_unsupported_warning_for_404_capabilities_probe',
            'test_issue5139_gateway_approval_offline_notice.py::test_gateway_chat_keeps_unsupported_warning_for_reachable_older_gateway',
            'test_issue5139_gateway_approval_offline_notice.py::test_gateway_chat_keeps_unsupported_warning_for_timeout_capabilities_probe',
            'test_issue5139_gateway_approval_offline_notice.py::test_gateway_chat_source_mentions_offline_warning_type',
            'test_issue7293_settle_marker.py::test_server_settle_marker_names_the_server_not_the_user[The WebUI server restarted to apply an update before this response finished]',
            'test_issue7293_settle_marker.py::test_server_settle_marker_names_the_server_not_the_user[The WebUI server shut down before this response finished]',
            'test_issue7293_settle_marker.py::test_user_cancel_marker_is_byte_identical',
            'test_issue7683_slash_menu_review_fixes.py::test_cli_only_explainer_labels_the_description_and_goal_hint_uses_brackets',
            'test_issue7683_slash_menu_review_fixes.py::test_helper_absent_fallback_blocks_non_dispatchable_without_throwing',
            'test_issue7683_slash_menu_review_fixes.py::test_hidden_agents_command_still_routes_through_explainer',
            'test_issue7683_slash_menu_review_fixes.py::test_prompt_style_command_leaves_the_de_slashed_text_in_the_composer',
            'test_issue7683_slash_menu_review_fixes.py::test_prompt_style_composer_restore_covers_the_no_arg_form',
            'test_issue7843_managed_agent_discovery_fallback.py::test_broken_bootstrap_still_warns_and_continues',
            'test_issue7937_start_ps1_exports_agent_dir.py::test_agent_dir_export_precedes_the_startup_banner',
            'test_start_ps1_launch_exec.py::test_no_agent_with_unreadable_legacy_home_reports_not_found',
            'test_japanese_locale.py::test_japanese_locale_includes_representative_translations',
            'test_kanban_bridge.py::test_issue7900_schedule_task_raises_when_agent_lacks_schedule_task',
            'test_korean_locale.py::test_korean_locale_includes_representative_translations',
            'test_korean_locale.py::test_korean_settings_detail_descriptions_are_translated',
            'test_nix_flake_module_source.py::test_nixos_module_defaults_to_loopback_with_explicit_firewall_opt_in',
            'test_plugins_panel.py::TestPluginsSettingsUi::test_plugins_panel_has_list_and_empty_state',
            'test_polish_locale.py::test_polish_locale_includes_representative_translations',
            'test_polish_locale.py::test_polish_settings_detail_descriptions_are_translated',
            'test_provider_mismatch.py::TestStreamingAuthErrorDetection::test_auth_error_hint_mentions_hermes_model',
            'test_pwa_notification_controls.py::test_settings_expose_permission_and_test_controls',
            'test_russian_locale.py::test_russian_locale_includes_representative_translations',
            'test_session_public_share_static.py::test_public_share_page_assets_exist',
            'test_sprint19.py::test_login_page_served',
            'test_sprint27.py::test_settings_default_bot_name',
            'test_sprint27.py::test_settings_empty_bot_name_defaults_to_hermes',
            'test_sprint27.py::test_settings_whitespace_bot_name_defaults_to_hermes',
            'test_sprint34.py::TestStatusFromRuntimeOAuth::test_oauth_incomplete_note_mentions_hermes_auth',
            'test_sprint42.py::TestRuntimeRouteInjection::test_runtime_provider_forwards_interim_assistant_callback',
            'test_stale_stream_cleanup.py::test_service_worker_cache_bumped_for_frontend_fix_delivery',
            'test_tls_aware_probe.py::test_ctl_status_survives_readonly_env_vars',
            'test_turkish_locale.py::test_turkish_locale_includes_representative_translations',
            'test_turkish_locale.py::test_turkish_settings_detail_descriptions_are_translated',
            'test_webui_gateway_chat_backend.py::test_gateway_http_401_with_key_suggests_key_mismatch',
            'test_windows_native_support.py::TestBootstrapWindowsUnblock::test_install_hermes_agent_allowed_in_wsl',
            'test_windows_native_support.py::TestBootstrapWindowsUnblock::test_install_hermes_agent_raises_on_windows',
            'test_zh_hant_locale.py::test_zh_hant_locale_includes_representative_translations',
        ],
    ),
    'updater': (
        'In-app updates are disabled; Altru is updated with deploy/macos/update.sh from release tags.',
        [
            'test_agent_runtime_revision_guard.py::test_async_compression_preserves_manual_restart_diagnostics[http-error]',
            'test_agent_runtime_revision_guard.py::test_async_compression_preserves_manual_restart_diagnostics[raised-error]',
            'test_agent_runtime_revision_guard.py::test_loaded_agent_runtime_fails_closed_after_source_revision_changes',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[absent-unverified]',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[active-active]',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[dangling-unknown]',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[dead-stale]',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[failed-exit-unverified]',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[future-unknown]',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[interrupted-exit-unverified]',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[invalid-encoding-unknown]',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[lazy-refresh-incomplete-incomplete]',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[malformed-unknown]',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[nonfinite-unknown]',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[over-age-stale]',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[oversized-pid-unknown]',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[separate-venv-incomplete-incomplete]',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[symlink-venv-incomplete-incomplete]',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[unreadable-unknown]',
            'test_agent_runtime_revision_guard.py::test_unverified_update_keeps_manual_409_without_restart[update-incomplete-incomplete]',
            'test_docker_experimental_update_notice.py::test_manual_update_instruction_matches_selected_channel[experimental-experimental]',
            'test_docker_experimental_update_notice.py::test_manual_update_instruction_matches_selected_channel[stable-latest]',
            'test_issue5959_manual_update_i18n.py::test_manual_update_instruction_uses_translation_helper',
            'test_issue6612_update_channel_autosave.py::test_settings_panel_posts_use_shared_queue_and_channel_is_single_owner',
            'test_issue8687_updater_restart_worker_isolation.py::TestRestartWorkerIsolation::test_a_later_update_is_not_refused',
            'test_issue8687_updater_restart_worker_isolation.py::TestRestartWorkerIsolation::test_update_checker_success_path_leaves_no_worker',
            'test_update_banner_fixes.py::TestAgentUpdateRequiresGatewayRestart::test_apply_update_agent_requires_gateway_restart',
            'test_update_banner_fixes.py::TestAgentUpdateRequiresGatewayRestart::test_apply_update_agent_stash_conflict_success_invokes_gateway_restart',
            'test_update_banner_fixes.py::TestAgentUpdateRequiresGatewayRestart::test_apply_update_agent_without_gateway_restart_result_fails',
            'test_update_banner_fixes.py::TestAgentUpdateRequiresGatewayRestart::test_apply_update_webui_does_not_call_gateway_restart',
            'test_update_banner_fixes.py::TestConflictError::test_conflict_returns_conflict_flag',
            'test_update_banner_fixes.py::TestSuccessfulUpdateReturnsRestartScheduled::test_apply_update_falls_back_to_tracking_branch_without_release_tags',
            'test_update_banner_fixes.py::TestSuccessfulUpdateReturnsRestartScheduled::test_apply_update_pulls_latest_release_tag_when_updates_are_release_based',
            'test_update_banner_fixes.py::TestSuccessfulUpdateReturnsRestartScheduled::test_apply_update_returns_restart_scheduled',
            'test_update_banner_fixes.py::TestUpdateBannerUx::test_manual_webui_banner_hides_apply_button',
            'test_update_banner_fixes.py::TestUpdateBannerUx::test_manual_webui_no_git_updates_are_bannerable_but_plain_no_git_stays_hidden',
            'test_update_banner_fixes.py::TestUpdateBannerUx::test_settings_manual_webui_update_includes_pull_guidance',
            'test_update_banner_fixes.py::TestUpdateBannerUx::test_settings_update_status_names_the_unit_once_in_every_locale',
            'test_update_channels.py::test_agent_resolution_identical_under_both_webui_channels',
            'test_update_channels.py::test_update_cache_scoped_by_channel',
            'test_update_checker.py::TestApplyUpdateDiagnostics::test_diverged_history_message_contains_compare_ref',
            'test_update_checker.py::TestApplyUpdateDiagnostics::test_diverged_history_returns_reset_hard_command',
            'test_update_checker.py::TestApplyUpdateDiagnostics::test_diverged_matching_is_case_insensitive',
            'test_update_checker.py::TestApplyUpdateDiagnostics::test_fetch_failure_does_not_attempt_pull',
            'test_update_checker.py::TestApplyUpdateDiagnostics::test_fetch_failure_for_agent_target',
            'test_update_checker.py::TestApplyUpdateDiagnostics::test_fetch_failure_returns_network_error_message',
            'test_update_checker.py::TestApplyUpdateDiagnostics::test_generic_failure_includes_truncated_git_output',
            'test_update_checker.py::TestApplyUpdateDiagnostics::test_no_tracking_alternate_phrasing',
            'test_update_checker.py::TestApplyUpdateDiagnostics::test_no_tracking_message_contains_compare_ref',
            'test_update_checker.py::TestApplyUpdateDiagnostics::test_no_tracking_returns_set_upstream_command',
            'test_update_checker.py::TestApplyUpdateDiagnostics::test_successful_update_still_returns_ok',
            'test_update_stash_recovery.py::test_pull_failure_stash_apply_conflict_cleans_worktree',
            'test_update_stash_recovery.py::test_pull_failure_stash_apply_conflict_preserves_diverged_flag',
            'test_update_stash_recovery.py::test_pull_failure_stash_apply_conflict_reset_failure_returns_error',
            'test_update_stash_recovery.py::test_pull_failure_stash_apply_recovery',
            'test_update_stash_recovery.py::test_pull_failure_stash_apply_recovery_discloses_drop_failure',
            'test_update_stash_recovery.py::test_pull_failure_stash_apply_recovery_warns_before_diverged_reset',
            'test_update_stash_recovery.py::test_pull_failure_untracked_overwrite_flags_conflict',
            'test_update_stash_recovery.py::test_stash_apply_conflict_preserves_stash',
            'test_update_stash_recovery.py::test_stash_apply_reset_failure_returns_error',
            'test_update_stash_recovery.py::test_stash_apply_success_discloses_drop_failure',
            'test_update_stash_recovery.py::test_stash_apply_success_drops_and_restarts',
            'test_updates.py::test_apply_clear_lock_with_no_lock_runs_normal_update',
            'test_updates.py::test_apply_fetch_failure_keeps_connectivity_guidance_for_network_errors',
            'test_updates.py::test_apply_fetch_failure_keeps_connectivity_guidance_for_remote_timeout',
            'test_updates.py::test_apply_fetch_failure_redacts_a_credentialed_operation_in_the_timeout_message',
            'test_updates.py::test_apply_fetch_failure_reports_cancelled_fetch_as_timeout',
            'test_updates.py::test_apply_update_fetch_failure_reports_local_diagnostic',
            'test_updates.py::test_apply_update_fetch_lock_error_does_not_attempt_pull',
            'test_updates.py::test_apply_update_fetch_lock_error_returns_lock_conflict',
            'test_updates.py::test_apply_update_fetches_tags_with_force',
            'test_updates.py::test_apply_update_pull_lock_error_returns_lock_conflict',
            'test_updates.py::test_apply_update_pull_lock_no_stash_when_clean',
            'test_updates.py::test_apply_update_pull_lock_restores_stash',
            'test_updates.py::test_apply_update_pull_timeout_does_not_leak_remote_token',
            'test_updates.py::test_apply_update_pull_timeout_returns_error_not_typeerror',
            'test_updates.py::test_apply_update_status_lock_error_returns_lock_conflict',
            'test_updates.py::test_check_for_updates_can_skip_agent_repo',
            'test_updates.py::test_check_for_updates_marks_every_cache_return[False-False]',
            'test_updates.py::test_check_for_updates_marks_every_cache_return[True-True]',
            'test_updates.py::test_update_cache_is_scoped_by_agent_inclusion',
        ],
    ),
    'workflows': (
        'Upstream workflows live in .github/workflows-disabled/; Altru CI is .github/workflows/altru-tests.yml.',
        [
            'test_ci_hygiene.py::test_github_actions_quotes_pyyaml_version_specifier',
            'test_ci_hygiene.py::test_local_test_runner_uses_supported_venv_before_pytest_collection',
            'test_ci_pr_concurrency.py::test_a_rerun_never_cancels_or_replaces_the_latest_heads_run[browser-smoke]',
            'test_ci_pr_concurrency.py::test_a_rerun_never_cancels_or_replaces_the_latest_heads_run[conversation-lifecycle]',
            'test_ci_pr_concurrency.py::test_a_rerun_never_cancels_or_replaces_the_latest_heads_run[docker-smoke]',
            'test_ci_pr_concurrency.py::test_a_rerun_never_cancels_or_replaces_the_latest_heads_run[docs-ci]',
            'test_ci_pr_concurrency.py::test_a_rerun_never_cancels_or_replaces_the_latest_heads_run[native-windows-startup]',
            'test_ci_pr_concurrency.py::test_a_rerun_never_cancels_or_replaces_the_latest_heads_run[tests]',
            'test_ci_pr_concurrency.py::test_every_pull_request_workflow_has_the_guard',
            'test_ci_pr_concurrency.py::test_first_attempt_of_a_pr_run_shares_the_pr_group_and_cancels[browser-smoke]',
            'test_ci_pr_concurrency.py::test_first_attempt_of_a_pr_run_shares_the_pr_group_and_cancels[conversation-lifecycle]',
            'test_ci_pr_concurrency.py::test_first_attempt_of_a_pr_run_shares_the_pr_group_and_cancels[docker-smoke]',
            'test_ci_pr_concurrency.py::test_first_attempt_of_a_pr_run_shares_the_pr_group_and_cancels[docs-ci]',
            'test_ci_pr_concurrency.py::test_first_attempt_of_a_pr_run_shares_the_pr_group_and_cancels[native-windows-startup]',
            'test_ci_pr_concurrency.py::test_first_attempt_of_a_pr_run_shares_the_pr_group_and_cancels[tests]',
            'test_ci_pr_concurrency.py::test_pushes_and_dispatches_get_a_unique_group_and_are_never_cancelled[push-browser-smoke]',
            'test_ci_pr_concurrency.py::test_pushes_and_dispatches_get_a_unique_group_and_are_never_cancelled[push-conversation-lifecycle]',
            'test_ci_pr_concurrency.py::test_pushes_and_dispatches_get_a_unique_group_and_are_never_cancelled[push-docker-smoke]',
            'test_ci_pr_concurrency.py::test_pushes_and_dispatches_get_a_unique_group_and_are_never_cancelled[push-docs-ci]',
            'test_ci_pr_concurrency.py::test_pushes_and_dispatches_get_a_unique_group_and_are_never_cancelled[push-native-windows-startup]',
            'test_ci_pr_concurrency.py::test_pushes_and_dispatches_get_a_unique_group_and_are_never_cancelled[push-tests]',
            'test_ci_pr_concurrency.py::test_pushes_and_dispatches_get_a_unique_group_and_are_never_cancelled[workflow_dispatch-browser-smoke]',
            'test_ci_pr_concurrency.py::test_pushes_and_dispatches_get_a_unique_group_and_are_never_cancelled[workflow_dispatch-conversation-lifecycle]',
            'test_ci_pr_concurrency.py::test_pushes_and_dispatches_get_a_unique_group_and_are_never_cancelled[workflow_dispatch-docker-smoke]',
            'test_ci_pr_concurrency.py::test_pushes_and_dispatches_get_a_unique_group_and_are_never_cancelled[workflow_dispatch-docs-ci]',
            'test_ci_pr_concurrency.py::test_pushes_and_dispatches_get_a_unique_group_and_are_never_cancelled[workflow_dispatch-native-windows-startup]',
            'test_ci_pr_concurrency.py::test_pushes_and_dispatches_get_a_unique_group_and_are_never_cancelled[workflow_dispatch-tests]',
            'test_ci_pr_concurrency.py::test_release_workflow_has_no_concurrency_group',
            'test_issue8106_first_start_ownership_race.py::test_docker_smoke_runs_first_start_race_proof',
            'test_static_js_scope_undef.py::test_ci_runs_scope_gate_with_require_eslint',
        ],
    ),
    'appearance': (
        'The inline theme/skin bootstrap moved to static/appearance.js (shared with the login page); guarded by tests/test_altru_appearance_skins.py.',
        [
            'test_6808_appearance_bootstrap_no_fabricated_choice.py::test_any_prior_state_still_normalises_and_persists[initial0-dark-default]',
            'test_6808_appearance_bootstrap_no_fabricated_choice.py::test_any_prior_state_still_normalises_and_persists[initial1-dark-mono]',
            'test_6808_appearance_bootstrap_no_fabricated_choice.py::test_any_prior_state_still_normalises_and_persists[initial2-light-mono]',
            'test_6808_appearance_bootstrap_no_fabricated_choice.py::test_fresh_browser_still_paints_dark',
            'test_6808_appearance_bootstrap_no_fabricated_choice.py::test_fresh_browser_writes_nothing',
            'test_6808_appearance_bootstrap_no_fabricated_choice.py::test_guard_is_on_the_pair_not_per_key',
            'test_6808_appearance_bootstrap_no_fabricated_choice.py::test_legacy_theme_migration_survives[monokai-dark-sisyphus]',
            'test_6808_appearance_bootstrap_no_fabricated_choice.py::test_legacy_theme_migration_survives[nord-dark-slate]',
            'test_6808_appearance_bootstrap_no_fabricated_choice.py::test_legacy_theme_migration_survives[oled-dark-default]',
            'test_6808_appearance_bootstrap_no_fabricated_choice.py::test_legacy_theme_migration_survives[slate-dark-slate]',
            'test_6808_appearance_bootstrap_no_fabricated_choice.py::test_legacy_theme_migration_survives[solarized-dark-poseidon]',
            'test_batch_fixes.py::TestSystemTheme::test_flicker_script_resolves_system',
            'test_catppuccin_skin.py::test_catppuccin_skin_in_client_and_server_allowlists',
            'test_catppuccin_skin.py::test_catppuccin_skin_is_opt_in_and_preserves_default_dark',
            'test_extension_theme_registration.py::test_prepaint_inline_script_preserves_unknown_skin',
            'test_geist_contrast_skin.py::test_geist_contrast_skin_is_registered_with_matching_key_and_label',
            'test_geist_contrast_skin.py::test_geist_contrast_slash_theme_uses_skin_value_key',
            'test_graphite_skin.py::test_graphite_skin_is_registered_end_to_end',
            'test_sienna_skin.py::test_default_theme_is_still_dark',
            'test_sienna_skin.py::test_sienna_skin_in_early_init_allowlist',
            'test_verdigris_skin.py::test_verdigris_i18n_lists_skin_in_all_locales',
            'test_verdigris_skin.py::test_verdigris_skin_is_registered_in_all_files',
            'test_zeus_skin.py::test_zeus_i18n_lists_skin_in_all_locales',
            'test_zeus_skin.py::test_zeus_skin_is_registered_in_all_files',
        ],
    ),
    'readme': (
        "README.md is Altru's own; upstream's is docs/UPSTREAM-README.md.",
        [
            'test_agent_context_docs.py::test_why_hermes_doc_remains_linked_from_readme',
            'test_chat_todos_tray_static.py::test_readme_documents_the_in_chat_task_list_and_its_todos_panel_effect',
            'test_issue3012_3006_docker_docs.py::test_docker_docs_warn_sudo_changes_home_bind_mount',
            'test_issue3012_3006_docker_docs.py::test_readme_common_failures_mentions_host_localhost',
            'test_issue513_wsl_autostart.py::test_wsl_autostart_docs_cover_session_and_task_scheduler_options',
            'test_nix_flake_module_source.py::test_readme_wires_published_agent_flake_package',
            'test_project_bindings_regate.py::test_docs_match_the_project_settings_ui',
            'test_project_bindings_uigate_1008.py::test_docs_describe_the_dormant_effort_binding',
            'test_readme_compat_section.py::test_readme_has_compatibility_section',
            'test_v050260_docker_invariants.py::test_readme_links_to_docker_md',
            'test_visible_session_limit_env.py::test_setting_is_documented',
        ],
    ),
    'desktop': (
        'Desktop/GUI history is recovered in an extra state.db pass outside the recent-session window, so call counts and window membership differ.',
        [
            'test_5306_subagent_sidebar_flicker.py::test_5305_subagent_of_desktop_parent_outside_window_stays_reachable[19]',
            'test_5306_subagent_sidebar_flicker.py::test_5305_subagent_of_desktop_parent_outside_window_stays_reachable[25]',
            'test_claude_code_session_import.py::test_get_cli_sessions_cache_invalidates_when_sqlite_wal_changes',
            'test_claude_code_session_import.py::test_idle_cli_cache_tests_survive_a_stream_left_registered_by_another_test[wal_invalidation]',
            'test_issue3585_cron_session_overflow.py::test_cron_sessions_recovered_by_second_pass',
            'test_pr7555_cli_session_availability.py::test_cache_owned_source_pass_failure_serves_fresh_incomplete_rows_uncached',
            'test_webhook_project_sessions.py::test_webhook_second_pass_keeps_older_project_rows_available',
        ],
    ),
    'taborder': (
        'The rail New chat button makes chat a reorderable tab.',
        [
            'test_sidebar_tab_order.py::test_backend_round_trip_and_validation_for_tab_order',
            'test_sidebar_tab_visibility.py::test_tab_order_excludes_always_visible_tabs',
        ],
    ),
    'version': (
        'The WebUI version token carries the brand revision (-brand<hash>) so branding changes refresh browser caches.',
        [
            'test_issue2695_packaged_runtime_layout.py::test_extracted_wheel_resolves_static_root_without_console_entrypoint_contract_change',
        ],
    ),
}

# Python 3.14 changed recursion-limit behaviour; whether these upstream tests
# fail depends on the platform's stack, so they are non-strict.
PY314_UPSTREAM = [
    'test_auth_session_persistence.py::TestSessionPersistence::test_session_recursion_failure_warns_with_state_dir_and_starts_fresh',
    'test_issue1257_llm_wiki_status.py::test_llm_wiki_status_last_updated_rechecks_status_file_identity',
    'test_session_lineage_metadata_api.py::test_branch_markers_report_fail_closed_unknown_state',
]


# Upstream tests that assume Linux and fail on our macOS hosts, also on plain
# upstream (verified 2026-11-16); they pass in Linux CI, so they are non-strict
# and apply on macOS only. Install requests, psutil and put uv on PATH first.
DARWIN_UPSTREAM = {
    "Apple's git always adds the osxkeychain credential helper": [
        'test_update_git_security.py::test_authenticated_fetch_never_runs_host_credential_helpers[updates-emulated-host-with-sentinel-helpers]',
        'test_update_git_security.py::test_authenticated_fetch_never_runs_host_credential_helpers[workspace-emulated-host-with-sentinel-helpers]',
        'test_update_git_security.py::test_authenticated_fetch_never_runs_host_credential_helpers[diagnostic-emulated-host-with-sentinel-helpers]',
        'test_workspace_git.py::test_git_fetch_never_runs_host_credential_helpers[emulated-host-with-sentinel-helpers]',
    ],
    'docker_init.bash needs Linux bash 4+; macOS ships bash 3.2': [
        'test_issue8113_venv_rebuild_keeps_previous.py::test_a_completed_rebuild_replaces_the_venv_and_removes_the_old_copies',
        'test_issue8113_venv_rebuild_keeps_previous.py::test_a_rebuild_without_a_named_interpreter_uses_uvs_default',
        'test_issue8113_venv_rebuild_keeps_previous.py::test_an_interrupted_rebuild_is_rolled_back_on_the_next_boot',
        'test_issue8524_docker_agent_uv_overrides.py::test_the_agents_overrides_are_passed_to_uv',
        'test_issue8524_docker_agent_uv_overrides.py::test_the_overrides_file_is_removed_afterwards',
        'test_issue8524_docker_agent_uv_overrides.py::test_an_unwritable_tmpdir_falls_back_to_the_stage_parent',
    ],
    'macOS temporary folders do not keep the setgid bit': [
        'test_5774b_atomic_config_writes.py::test_atomic_write_preserves_existing_permissions',
    ],
    'Starting a full server with the installed Hermes runtime can exceed the 45 s limit on these hosts': [
        'test_conftest_skills_isolation.py::test_skill_writes_never_touch_the_real_skills_dir[no-agent]',
        'test_conftest_skills_isolation.py::test_skill_writes_never_touch_the_real_skills_dir[agent]',
    ],
}


def _index():
    index = {}
    for name, (reason, nodeids) in DIVERGENCES.items():
        for nodeid in nodeids:
            index[nodeid] = (f'Altru {name}: {reason}', True)
    if sys.version_info[:2] >= (3, 14):
        for nodeid in PY314_UPSTREAM:
            index[nodeid] = ('Upstream test is platform-dependent under Python 3.14', False)
    if sys.platform == 'darwin':
        for reason, nodeids in DARWIN_UPSTREAM.items():
            for nodeid in nodeids:
                index.setdefault(nodeid, (f'macOS host: {reason}', False))
    return index


def pytest_collection_modifyitems(config, items):
    index = _index()
    for item in items:
        nodeid = item.nodeid.split('tests/', 1)[-1]
        entry = index.get(nodeid)
        if entry:
            reason, strict = entry
            item.add_marker(pytest.mark.xfail(reason=reason, strict=strict))
