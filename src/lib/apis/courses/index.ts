// src/lib/apis/courses/index.ts
import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getCourses = async (token: string) => {
	let error: unknown = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/courses`, {
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

	return data;
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

	return data;
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

	const res = await fetch(`${WEBUI_API_BASE_URL}/courses/id/${id}/update`, {
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
