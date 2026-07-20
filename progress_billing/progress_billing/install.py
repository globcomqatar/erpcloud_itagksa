from progress_billing.setup.custom_fields import sync_custom_fields


def after_install():
	sync_custom_fields()
