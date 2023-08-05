import React, { Component } from "react";
import { render } from "react-dom";


export default class App extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <div>
        <h1> React Code Test </h1>
      </div>
    );
  }
}

const appDiv = document.getElementById("app");
render(<App />, appDiv);




/*import react, {Component} from "react";
import {render} from "react-dom";

export default class App extends Component {
    constructor(props) {
        super(props);
    }
    render() {
        return <h1> Testing React Code </h1> missed paratnthesis
    }
}

const appDiv = document.getElementById("app");
render(<App />, appDiv);
*/