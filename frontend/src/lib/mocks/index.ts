export const mockUser = {
	id: '00000000-0000-0000-0000-000000000001',
	username: 'admin',
	email: 'admin@example.com',
	full_name: 'System Administrator',
	is_superuser: true,
	roles: ['SystemManager']
};

export const mockToken = 'mock-token-for-admin';

export interface MockEntity {
	name: string;
	label: string;
	module: string;
	group: string;
	icon: string;
	in_sidebar: boolean;
	permissions?: Record<string, boolean>;
	fields?: Record<string, any>[];
}

export const mockEntities: MockEntity[] = [
	{
		name: 'user',
		label: 'User',
		module: 'core',
		group: 'Authentication',
		icon: 'user',
		in_sidebar: true,
		permissions: {
			can_read: true,
			can_create: true,
			can_update: true,
			can_delete: true,
			can_select: true,
			can_export: true,
			can_import: true,
			in_sidebar: true
		}
	},
	{
		name: 'role',
		label: 'Role',
		module: 'core',
		group: 'Authentication',
		icon: 'shield',
		in_sidebar: true,
		permissions: {
			can_read: true,
			can_create: true,
			can_update: true,
			can_delete: true,
			can_select: true,
			can_export: true,
			can_import: true,
			in_sidebar: true
		}
	},
	{
		name: 'workflow',
		label: 'Workflow',
		module: 'core',
		group: 'Workflow',
		icon: 'workflow',
		in_sidebar: true,
		permissions: {
			can_read: true,
			can_create: true,
			can_update: true,
			can_delete: true,
			can_select: true,
			can_export: true,
			can_import: true,
			in_sidebar: true
		}
	},
	{
		name: 'audit_log',
		label: 'Audit Log',
		module: 'core',
		group: 'System',
		icon: 'clipboard-list',
		in_sidebar: true,
		permissions: {
			can_read: true,
			can_create: false,
			can_update: false,
			can_delete: false,
			can_select: true,
			can_export: true,
			can_import: false,
			in_sidebar: true
		}
	},
	{
		name: 'error_log',
		label: 'Error Log',
		module: 'core',
		group: 'System',
		icon: 'alert-circle',
		in_sidebar: true,
		permissions: {
			can_read: true,
			can_create: false,
			can_update: false,
			can_delete: false,
			can_select: true,
			can_export: true,
			can_import: false,
			in_sidebar: true
		}
	},
	{
		name: 'series',
		label: 'Series',
		module: 'core',
		group: 'Framework',
		icon: 'hash',
		in_sidebar: true,
		permissions: {
			can_read: true,
			can_create: true,
			can_update: true,
			can_delete: true,
			can_select: true,
			can_export: true,
			can_import: true,
			in_sidebar: true
		}
	},
	{
		name: 'user_settings',
		label: 'User Settings',
		module: 'core',
		group: 'Framework',
		icon: 'settings',
		in_sidebar: true,
		permissions: {
			can_read: true,
			can_create: true,
			can_update: true,
			can_delete: true,
			can_select: true,
			can_export: true,
			can_import: true,
			in_sidebar: true
		}
	}
];

const userFields = [
	{ name: 'username', label: 'Username', field_type: 'string', in_list_view: true, required: true },
	{ name: 'email', label: 'Email', field_type: 'email', in_list_view: true, required: true },
	{ name: 'full_name', label: 'Full Name', field_type: 'string', in_list_view: true, required: true },
	{ name: 'is_active', label: 'Active', field_type: 'boolean', in_list_view: true, required: false },
	{ name: 'is_superuser', label: 'Superuser', field_type: 'boolean', in_list_view: true, required: false }
];

const roleFields = [
	{ name: 'name', label: 'Name', field_type: 'string', in_list_view: true, required: true },
	{ name: 'description', label: 'Description', field_type: 'text', in_list_view: true, required: false }
];

const workflowFields = [
	{ name: 'name', label: 'Name', field_type: 'string', in_list_view: true, required: true },
	{ name: 'target_entity', label: 'Target Entity', field_type: 'string', in_list_view: true, required: true },
	{ name: 'is_active', label: 'Active', field_type: 'boolean', in_list_view: true, required: false }
];

const auditLogFields = [
	{ name: 'entity_name', label: 'Entity', field_type: 'string', in_list_view: true, required: true },
	{ name: 'action', label: 'Action', field_type: 'string', in_list_view: true, required: true },
	{ name: 'record_id', label: 'Record ID', field_type: 'string', in_list_view: true, required: false },
	{ name: 'user_id', label: 'User ID', field_type: 'string', in_list_view: true, required: false },
	{ name: 'created_at', label: 'Created At', field_type: 'datetime', in_list_view: true, required: false }
];

const errorLogFields = [
	{ name: 'message', label: 'Message', field_type: 'text', in_list_view: true, required: true },
	{ name: 'stack', label: 'Stack', field_type: 'text', in_list_view: false, required: false },
	{ name: 'created_at', label: 'Created At', field_type: 'datetime', in_list_view: true, required: false }
];

const seriesFields = [
	{ name: 'name', label: 'Name', field_type: 'string', in_list_view: true, required: true },
	{ name: 'current', label: 'Current', field_type: 'integer', in_list_view: true, required: true }
];

const userSettingsFields = [
	{ name: 'user_id', label: 'User ID', field_type: 'string', in_list_view: true, required: true },
	{ name: 'theme', label: 'Theme', field_type: 'string', in_list_view: true, required: false },
	{ name: 'dashboard_selections', label: 'Dashboard Selections', field_type: 'json', in_list_view: false, required: false }
];

export const mockFields: Record<string, Record<string, any>[]> = {
	user: userFields,
	role: roleFields,
	workflow: workflowFields,
	audit_log: auditLogFields,
	error_log: errorLogFields,
	series: seriesFields,
	user_settings: userSettingsFields
};

export const mockRecords: Record<string, Record<string, any>[]> = {
	user: [
		{ id: 'u1', username: 'admin', email: 'admin@example.com', full_name: 'System Administrator', is_active: true, is_superuser: true },
		{ id: 'u2', username: 'john.doe', email: 'john@example.com', full_name: 'John Doe', is_active: true, is_superuser: false },
		{ id: 'u3', username: 'jane.smith', email: 'jane@example.com', full_name: 'Jane Smith', is_active: true, is_superuser: false }
	],
	role: [
		{ id: 'r1', name: 'SystemManager', description: 'Full system access' },
		{ id: 'r2', name: 'User', description: 'Standard user' },
		{ id: 'r3', name: 'Manager', description: 'Can manage records' }
	],
	workflow: [
		{ id: 'w1', name: 'User Approval', target_entity: 'user', is_active: true },
		{ id: 'w2', name: 'Role Lifecycle', target_entity: 'role', is_active: true }
	],
	audit_log: [
		{ id: 'a1', entity_name: 'user', action: 'create', record_id: 'u2', user_id: 'u1', created_at: '2026-07-12T10:00:00Z' },
		{ id: 'a2', entity_name: 'role', action: 'update', record_id: 'r2', user_id: 'u1', created_at: '2026-07-12T11:00:00Z' }
	],
	error_log: [
		{ id: 'e1', message: 'Connection timeout', stack: 'Traceback...', created_at: '2026-07-12T12:00:00Z' },
		{ id: 'e2', message: 'Invalid token', stack: 'Traceback...', created_at: '2026-07-12T12:30:00Z' }
	],
	series: [
		{ id: 's1', name: 'USER', current: 42 },
		{ id: 's2', name: 'ROLE', current: 7 }
	],
	user_settings: [
		{ id: 'us1', user_id: 'u1', theme: 'system', dashboard_selections: { dashboard: ['User', 'Role'] } },
		{ id: 'us2', user_id: 'u2', theme: 'light', dashboard_selections: {} }
	]
};

export async function mockLogin(username: string, password: string) {
	await new Promise((resolve) => setTimeout(resolve, 300));
	if (username !== 'admin' || password !== 'admin') {
		throw new Error('Invalid username or password');
	}
	return {
		access_token: mockToken,
		refresh_token: mockToken,
		token_type: 'bearer',
		user: mockUser,
		feature_flags: {}
	};
}

export async function getMockEntities() {
	await new Promise((resolve) => setTimeout(resolve, 200));
	return { status: 'success', data: mockEntities };
}

export async function getMockEntityMeta(entity: string) {
	await new Promise((resolve) => setTimeout(resolve, 200));
	const found = mockEntities.find((e) => e.name === entity);
	if (!found) throw new Error(`Entity '${entity}' not found`);
	return {
		status: 'success',
		data: {
			name: found.name,
			label: found.label,
			module: found.module,
			group: found.group,
			icon: found.icon,
			in_sidebar: found.in_sidebar,
			permissions: found.permissions,
			fields: mockFields[entity] || []
		}
	};
}

export async function listMockEntity(entity: string) {
	await new Promise((resolve) => setTimeout(resolve, 250));
	const records = mockRecords[entity] || [];
	return {
		status: 'success',
		data: records,
		total: records.length,
		page: 1,
		page_size: 20
	};
}

export async function getMockEntityRecord(entity: string, id: string) {
	await new Promise((resolve) => setTimeout(resolve, 150));
	const record = mockRecords[entity]?.find((r) => String(r.id) === id);
	if (!record) throw new Error('Record not found');
	return { status: 'success', data: record };
}

export async function saveMockEntity(entity: string, data: Record<string, any>, id?: string) {
	await new Promise((resolve) => setTimeout(resolve, 300));
	return { status: 'success', data: { id: id || crypto.randomUUID(), ...data } };
}

export async function deleteMockEntity(entity: string, id: string) {
	await new Promise((resolve) => setTimeout(resolve, 200));
	return { status: 'success', data: { id } };
}
