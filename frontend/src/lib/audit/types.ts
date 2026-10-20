export interface AuditLog {
	id: string;
	reference_entity: string;
	reference_id: string;
	action: string;
	old_values?: any;
	new_values?: any;
	actor_id?: string;
	ip_address?: string;
	timestamp?: string;
	created_at?: string;
	updated_at?: string;
}

export interface Ledger {
	id: string;
	reference_entity: string;
	reference_id: string;
	user_id: string;
	amount: number;
	entry_type: 'credit' | 'debit' | string;
	description?: string;
	period?: string;
	created_at?: string;
	updated_at?: string;
}
