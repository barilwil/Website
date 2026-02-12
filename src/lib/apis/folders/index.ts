import { WEBUI_API_BASE_URL } from '$lib/constants';

type FolderForm = {
	name?: string;
	data?: Record<string, any>;
	meta?: Record<string, any>;
	// NEW: match backend
	context_type?: 'general' | 'lab' | 'channel';
	course_id?: string | null;
	lab_id?: string | null;
};


export const createNewFolder = async (token: string, folderForm: FolderForm) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(folderForm)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type FolderContext = {
	context_type?: 'general' | 'lab' | 'channel';
	course_id?: string | null;
	lab_id?: string | null;
};

export const getFolders = async (token: string = '', context?: FolderContext) => {
	let error = null;

	const params = new URLSearchParams();
	if (context?.context_type) params.set('context_type', context.context_type);
	if (context?.course_id) params.set('course_id', context.course_id);
	if (context?.lab_id) params.set('lab_id', context.lab_id);

	const qs = params.toString();
	const url = `${WEBUI_API_BASE_URL}/folders/${qs ? `?${qs}` : ''}`;

	const res = await fetch(url, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getFolderById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/${id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateFolderById = async (token: string, id: string, folderForm: FolderForm) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/${id}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(folderForm)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateFolderIsExpandedById = async (
	token: string,
	id: string,
	isExpanded: boolean
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/${id}/update/expanded`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			is_expanded: isExpanded
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateFolderParentIdById = async (token: string, id: string, parentId?: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/${id}/update/parent`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			parent_id: parentId
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type FolderItems = {
	chat_ids: string[];
	file_ids: string[];
};

export const updateFolderItemsById = async (token: string, id: string, items: FolderItems) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/${id}/update/items`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			items: items
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteFolderById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/${id}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
