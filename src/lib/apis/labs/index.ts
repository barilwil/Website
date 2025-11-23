import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getLabById = async (token: string, id: string) => {
	let error: unknown = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/labs/id/${id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	}).catch((e) => {
		error = e;
		return null;
	});

	if (!res) throw error ?? new Error('Network error');

	const data = await res.json().catch(() => ({}));

	if (!res.ok) {
		error = (data && (data.detail || data.error)) || res.statusText;
	}

	if (error) throw error;

	return data;
};

export const createLab = async (
	token: string,
	lab: {
		course_id: string;
		name: string;
		description?: string;
		enabled?: boolean;
	}
) => {
	let error: unknown = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/labs/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(lab)
	}).catch((e) => {
		error = e;
		return null;
	});

	if (!res) throw error ?? new Error('Network error');

	const data = await res.json().catch(() => ({}));

	if (!res.ok) {
		error = (data && (data.detail || data.error)) || res.statusText;
	}

	if (error) throw error;

	return data;
};

export const updateLab = async (
	token: string,
	id: string,
	update: Partial<{ name: string; description: string; enabled: boolean }>
) => {
	let error: unknown = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/labs/id/${id}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(update)
	}).catch((e) => {
		error = e;
		return null;
	});

	if (!res) throw error ?? new Error('Network error');

	const data = await res.json().catch(() => ({}));

	if (!res.ok) {
		error = (data && (data.detail || data.error)) || res.statusText;
	}

	if (error) throw error;

	return data;
};


export const deleteLab = async (token: string, id: string) => {
	let error: unknown = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/labs/id/${id}/delete`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	}).catch((e) => {
		error = e;
		return null;
	});

	if (!res) throw error ?? new Error('Network error');

	const data = await res.json().catch(() => ({}));

	if (!res.ok) {
		error = (data && (data.detail || data.error)) || res.statusText;
	}

	if (error) throw error;

	return data as boolean;
};
