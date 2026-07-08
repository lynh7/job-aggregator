// @ts-nocheck
import { render } from 'preact';
import '@shoelace-style/shoelace/dist/themes/light.css';
import 'src/styles.css';
import { App } from 'src/app';

render(<App />, document.getElementById('app') as HTMLElement);
