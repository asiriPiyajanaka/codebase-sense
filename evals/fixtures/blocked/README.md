# Cancellation verification

Cancellation must persist before the caller receives success. The integration
check needs a provisioned `WAREHOUSE_TEST_DATABASE` and its driver. They are not
provided in this checkout. Do not create a fake service or change test settings.

Run: `python3 -m unittest discover -s tests -v`.
