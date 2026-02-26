// src/lib/apis/courses/index.ts
import { WEBUI_API_BASE_URL } from '$lib/constants';

const asArray = <T = unknown>(data: unknown): T[] => {
	if (Array.isArray(data)) return data as T[];
	if (data && typeof data === 'object') {
		const obj = data as Record<string, unknown>;
		const candidates = [obj.courses, obj.labs, obj.items, obj.data, obj.results];
		for (const c of candidates) if (Array.isArray(c)) return c as T[];
	}
	return [];
};

export const getCourses = async (token: string) => {
	let error: unknown = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/courses/`, {
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

	if (!res) {
		throw error ?? new Error('Network error');
	}

	const data = await res.json().catch(() => ({}));

	if (!res.ok) {
		error = (data && (data.detail || data.error)) || res.statusText;
	}

	if (error) {
		throw error;
	}

	return asArray(data);
};

export const getLabsForCourse = async (token: string, courseId: string) => {
	let error: unknown = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/courses/id/${courseId}/labs`, {
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

	if (!res) {
		throw error ?? new Error('Network error');
	}

	const data = await res.json().catch(() => ({}));

	if (!res.ok) {
		error = (data && (data.detail || data.error)) || res.statusText;
	}

	if (error) {
		throw error;
	}

	return asArray(data);
};

export const createCourse = async (
	token: string,
	course: {
		code: string;
		name: string;
		description?: string;
		enabled?: boolean;
		meta?: Record<string, unknown>;
	}
) => {
	let error: unknown = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/courses/create`, {
		// FastAPI route is POST /api/v1/courses/create
		// Using PUT here triggers 405 Method Not Allowed.
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(course)
	}).catch((e) => {
		error = e;
		return null;
	});

	if (!res) {
		throw error ?? new Error('Network error');
	}

	const data = await res.json().catch(() => ({}));

	if (!res.ok) {
		error = (data && (data.detail || data.error)) || res.statusText;
	}

	if (error) {
		throw error;
	}

	return data;
};

export const updateCourse = async (
	token: string,
	id: string,
	update: Partial<{
		code: string;
		name: string;
		description: string;
		enabled: boolean;
		meta: Record<string, unknown>;
	}>
) => {
	let error: unknown = null;

	// Backends vary on which method/path they use for updates.
	// Try the most likely combos in order to avoid a 405 (Method Not Allowed).
	const tryRequests = async () => {
		const headers = {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		};

		const body = JSON.stringify(update);

		const attempts: Array<[string, string]> = [
			[`${WEBUI_API_BASE_URL}/courses/id/${id}/update`, 'PUT'],
			[`${WEBUI_API_BASE_URL}/courses/id/${id}/update/`, 'PUT'],
			[`${WEBUI_API_BASE_URL}/courses/id/${id}/update`, 'POST'],
			[`${WEBUI_API_BASE_URL}/courses/id/${id}/update/`, 'POST'],
			// common REST alternative
			[`${WEBUI_API_BASE_URL}/courses/id/${id}`, 'PUT'],
			[`${WEBUI_API_BASE_URL}/courses/id/${id}`, 'POST']
		];

		for (const [url, method] of attempts) {
			const r = await fetch(url, { method, headers, body }).catch((e) => {
				error = e;
				return null;
			});
			if (!r) continue;
			// 405 = wrong method for this path → keep trying
			if (r.status === 405) continue;
			return r;
		}
		return null;
	};

	const res = await tryRequests();

	if (!res) {
		throw error ?? new Error('Network error');
	}

	const data = await res.json().catch(() => ({}));

	if (!res.ok) {
		error = (data && (data.detail || data.error)) || res.statusText;
	}

	if (error) {
		throw error;
	}

	return data;
};

export const deleteCourse = async (token: string, id: string) => {
	let error: unknown = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/courses/id/${id}/delete`, {
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
