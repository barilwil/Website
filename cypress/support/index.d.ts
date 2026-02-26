// load the global Cypress types
/// <reference types="cypress" />

/*
This TypeScript declaration file extends Cypress’s Chainable interface
to type custom E2E helper commands, enabling IntelliSense and compile-time
safety without affecting runtime behavior.
 */

declare namespace Cypress {
	interface Chainable {
		login(email: string, password: string): Chainable<Element>;
		register(name: string, email: string, password: string): Chainable<Element>;
		registerAdmin(): Chainable<Element>;
		loginAdmin(): Chainable<Element>;
		uploadTestDocument(suffix: any): Chainable<Element>;
		deleteTestDocument(suffix: any): Chainable<Element>;
	}
}
