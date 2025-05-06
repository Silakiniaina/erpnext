frappe.pages['data-import-page'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'data-import',
		single_column: true
	});
}