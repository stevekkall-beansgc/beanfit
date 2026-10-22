import XCTest

final class TextDraftUITests: XCTestCase {
    override func setUpWithError() throws { continueAfterFailure = false }
    func testPocket() { exercise(bundle:"com.beanlabs.BeanFitPocket", entry:"Write with local AI") }
    func testBeanSprout() { exercise(bundle:"com.jumpingbeans.v2.imessageprototype", entry:"open-local-text") }

    private func wait(_ element: XCUIElement, enabled: Bool = true, timeout: TimeInterval = 20) {
        let predicate = NSPredicate(format:"exists == true AND enabled == %@", NSNumber(value:enabled))
        XCTAssertEqual(XCTWaiter.wait(for:[XCTNSPredicateExpectation(predicate:predicate,object:element)],timeout:timeout),.completed)
    }
    private func replace(_ editor: XCUIElement, with value: String) {
        editor.tap()
        let old = editor.value as? String ?? ""
        editor.typeText(String(repeating:XCUIKeyboardKey.delete.rawValue,count:old.count) + value)
    }
    private func exercise(bundle: String, entry: String) {
        let app = XCUIApplication(bundleIdentifier:bundle)
        app.launchArguments = ["--text-ui-test"]
        app.launch()
        XCTAssertTrue(app.buttons[entry].waitForExistence(timeout:15))
        app.buttons[entry].tap()
        let write = app.buttons["writeTextDraft"]
        XCTAssertTrue(write.waitForExistence(timeout:10))
        XCTAssertFalse(write.isEnabled)
        app.buttons["loadTextModel"].tap()
        wait(write)
        let editor = app.textViews["textDraftInput"]
        replace(editor,with:"The meeting is Thursday. Bring a blue folder.")
        write.tap()
        let output = app.staticTexts["textDraftOutput"]
        XCTAssertTrue(output.waitForExistence(timeout:20))
        XCTAssertTrue(output.label.lowercased().contains("thursday"))
        XCTAssertTrue(output.label.lowercased().contains("blue"))
        app.swipeUp()
        app.buttons["Copy reviewed draft"].tap()
        XCTAssertTrue(app.staticTexts["textDraftStatus"].label.contains("Draft copied"))
        app.swipeDown()
        replace(editor,with:"Please return the green folder on Monday.")
        XCTAssertFalse(output.exists)
        XCTAssertFalse(app.buttons["Copy reviewed draft"].exists)
        app.swipeUp() // Dismiss the editor keyboard before leaving the app.
        XCUIDevice.shared.press(.home)
        // Observe after a real background/foreground transition, not a notification injection.
        Thread.sleep(forTimeInterval:2)
        app.activate()
        wait(write,enabled:false)
        app.swipeDown()
        app.buttons["loadTextModel"].tap()
        wait(write)
        app.navigationBars.buttons["Done"].tap()
        XCTAssertTrue(app.buttons[entry].waitForExistence(timeout:10))
        app.terminate()
    }
}
