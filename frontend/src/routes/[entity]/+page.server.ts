import { redirect } from '@sveltejs/kit';

export const load = async ({ params, fetch }) => {
	const slug = params.entity;
	const res = await fetch(`/api/utils/go/${encodeURIComponent(slug)}`, {
		method: 'GET',
		redirect: 'manual',
	});

	if (res.status >= 300 && res.status < 400) {
		const location = res.headers.get('location');
		if (location) {
			throw redirect(307, location);
		}
	}

	return {};
};
