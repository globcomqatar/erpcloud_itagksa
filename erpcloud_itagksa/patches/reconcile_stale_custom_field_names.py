from erpcloud_itagksa.install import reconcile_stale_custom_field_names


def execute():
	"""Migrate-path counterpart to the before_install hook.

	A fresh install runs before_install; a re-migrate (e.g. retry after a
	half-failed install) runs this pre_model_sync patch before fixtures sync.
	Shared idempotent logic, so a redeploy self-heals either way.
	"""
	reconcile_stale_custom_field_names()
